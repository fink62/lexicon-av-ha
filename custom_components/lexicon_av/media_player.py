"""Lexicon AV Receiver Media Player entity."""
import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_INPUT_MAPPINGS,
    DEFAULT_PORT,
    DEFAULT_NAME,
    LEXICON_INPUTS,
)
from .lexicon_protocol import LexiconProtocol

# Polling intervals (state-aware v2.0.0)
SCAN_INTERVAL_ON = 30       # 30s when receiver is ON (full query set)
SCAN_INTERVAL_OFF = 60      # 60s when receiver is OFF (power query only)
SCAN_INTERVAL_STARTUP = 5   # 5s delay before first poll

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lexicon media player."""
    host = config_entry.data[CONF_HOST]
    port = config_entry.data.get(CONF_PORT, DEFAULT_PORT)
    input_mappings = config_entry.data.get(CONF_INPUT_MAPPINGS, {})

    # Create protocol instance
    protocol = LexiconProtocol(host, port)

    # Create media player entity
    async_add_entities([LexiconMediaPlayer(protocol, input_mappings)], True)


class LexiconMediaPlayer(MediaPlayerEntity):
    """Representation of a Lexicon AV Receiver Media Player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False  # We use custom polling

    def __init__(self, protocol: LexiconProtocol, input_mappings: dict) -> None:
        """Initialize the media player."""
        self._protocol = protocol
        self._input_mappings = input_mappings
        
        # Build reverse mapping: custom_name -> physical_input
        # input_mappings from config has: physical_input -> custom_name
        # We need: custom_name -> physical_input for lookups
        self._name_to_physical = {}
        if input_mappings:
            for physical, custom_name in input_mappings.items():
                if custom_name:  # Only if user provided a custom name
                    self._name_to_physical[custom_name] = physical
        
        # Also build physical_name -> custom_name for displaying current source
        self._physical_to_name = {}
        if input_mappings:
            for physical, custom_name in input_mappings.items():
                if custom_name:
                    self._physical_to_name[physical] = custom_name
        
        # Build source list from custom names, or physical names if no mapping
        # Format: "Custom Name (PHYSICAL)" or just "PHYSICAL"
        if self._name_to_physical:
            # Show custom names with physical in brackets
            self._source_list = [f"{custom} ({physical})" for custom, physical in self._name_to_physical.items()]
            # Also add any unmapped physical inputs
            for physical in LEXICON_INPUTS.keys():
                if physical not in self._physical_to_name:
                    self._source_list.append(physical)
        else:
            # No mappings - show only physical names
            self._source_list = list(LEXICON_INPUTS.keys())
        
        self._current_source = None
        self._state = MediaPlayerState.OFF  # Will be updated by first poll
        self._is_volume_muted = False
        self._volume_level = None  # Will be set by first poll
        self._cancel_polling = None
        self._poll_count = 0  # Track number of polls for startup optimization
        
        # Audio status attributes
        self._audio_format = None
        self._decode_mode = None
        self._sample_rate = None
        self._direct_mode = None
        
        # Power transition lock
        self._power_transition_until = None  # Timestamp until which to ignore power queries
        self._ready = False  # Indicates if receiver is fully operational
        self._last_successful_poll = None  # Track last successful query timestamp

        # Connection lock — prevents race conditions between polling and commands
        self._connection_lock = asyncio.Lock()
        self._last_operation = None  # Timestamp of last disconnect

        # Set unique ID
        self._attr_unique_id = f"lexicon_av_{protocol._host}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, protocol._host)},
            "name": DEFAULT_NAME,
            "manufacturer": "Lexicon",
            "model": "AV Receiver",
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass - start polling."""
        await super().async_added_to_hass()

        # Schedule first poll after startup delay
        _LOGGER.info("Starting state-aware polling (ON=%ds, OFF=%ds)",
                     SCAN_INTERVAL_ON, SCAN_INTERVAL_OFF)
        self._schedule_next_poll(SCAN_INTERVAL_STARTUP)

    async def _execute_with_connection(self, operation_func, operation_name: str):
        """Execute an operation within a connect/disconnect lifecycle.

        Ensures:
        - Only one operation at a time (lock prevents race with polling)
        - Clean connect/disconnect lifecycle per operation
        - Minimal connection hold time for app availability

        Args:
            operation_func: Async function to execute while connected.
            operation_name: Name for logging (e.g. "turn_on", "volume_up").

        Returns:
            Result from operation_func, or None on error.
        """
        async with self._connection_lock:
            try:
                if not await self._protocol.connect():
                    _LOGGER.error("Could not connect for %s", operation_name)
                    return None

                try:
                    _LOGGER.debug("Executing: %s", operation_name)
                    result = await operation_func()
                    return result
                finally:
                    await self._protocol.disconnect()
                    self._last_operation = datetime.now()

            except Exception as e:
                _LOGGER.error("Error in %s: %s", operation_name, e, exc_info=True)
                return None

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        
        # Stop polling
        if self._cancel_polling:
            self._cancel_polling()
            self._cancel_polling = None
            _LOGGER.info("Status polling stopped")
        
        await self._protocol.disconnect()
        _LOGGER.info("Entity removed, connection closed")

    def _schedule_next_poll(self, delay: int) -> None:
        """Schedule the next poll after delay seconds.

        Uses async_call_later for dynamic intervals based on receiver state:
        - ON:  30s (need timely status updates)
        - OFF: 60s (power check only, minimize overhead)
        """
        if self._cancel_polling:
            self._cancel_polling()
        self._cancel_polling = async_call_later(
            self.hass, delay, self._trigger_poll
        )
        _LOGGER.debug("Next poll in %ds", delay)

    @callback
    def _trigger_poll(self, _=None):
        """Timer callback — triggers async poll."""
        self.hass.async_create_task(self._async_polling_update())

    async def _async_polling_update(self, now=None) -> None:
        """Periodic status update with state-aware rescheduling."""
        self._poll_count += 1
        _LOGGER.debug("Poll #%d triggered", self._poll_count)

        await self._async_update_status()

        # Schedule next poll based on current state
        interval = SCAN_INTERVAL_ON if self._state == MediaPlayerState.ON else SCAN_INTERVAL_OFF
        self._schedule_next_poll(interval)

    async def _async_update_status(self) -> None:
        """Query receiver status with fast-fail and state-aware queries.

        v2.0.0 strategy:
        1. Connect (evicts app — hold time must be minimal)
        2. Power query with fast-fail (1s timeout)
           - None → receiver unreachable, abort immediately (~1.05s hold)
           - False → standby, done (~0.19s hold)
           - True → query full status (~1.35s hold)
        3. Disconnect (app can reconnect)

        Connection hold time budget:
        - ON:  ~1.35s / 30s = 95.5% app availability
        - OFF: ~1.05s / 60s = 98.2% app availability
        """
        async with self._connection_lock:
            # Connect for this poll cycle
            if not await self._protocol.connect():
                _LOGGER.warning("Could not connect for poll #%d", self._poll_count)
                self._ready = False
                self._state = MediaPlayerState.OFF
                self.async_write_ha_state()
                return

            try:
                # --- FAST-FAIL: Power query first ---
                power_state = None
                if self._power_transition_until and datetime.now() < self._power_transition_until:
                    # Boot transition: use optimistic state
                    power_state = (self._state == MediaPlayerState.ON)
                    remaining = (self._power_transition_until - datetime.now()).total_seconds()
                    _LOGGER.debug("Boot transition (%.1fs remaining), optimistic ON", remaining)
                else:
                    power_state = await self._protocol.get_power_state(timeout=1.0)

                if power_state is None:
                    # Receiver not responding — fast-fail, abort entire cycle
                    _LOGGER.debug("Power query timeout — receiver OFF/unreachable")
                    self._state = MediaPlayerState.OFF
                    self._ready = False
                    self.async_write_ha_state()
                    return

                if not power_state:
                    # Receiver in standby — no further queries needed
                    self._state = MediaPlayerState.OFF
                    self._ready = False
                    self._power_transition_until = None
                    self._audio_format = None
                    self._decode_mode = None
                    self._sample_rate = None
                    self._direct_mode = None
                    self.async_write_ha_state()
                    return

                # --- Receiver is ON: full query set ---

                # Detect OFF → ON transition
                if self._state == MediaPlayerState.OFF:
                    _LOGGER.info("State changed: OFF -> ON (boot stabilization 10s)")
                    self._power_transition_until = datetime.now() + timedelta(seconds=10)
                    self._ready = False
                self._state = MediaPlayerState.ON

                # Core status queries (cached on failure)
                volume = await self._protocol.get_volume()
                if volume is not None:
                    self._volume_level = round(volume / 99.0, 2)

                mute = await self._protocol.get_mute_state()
                if mute is not None:
                    self._is_volume_muted = mute

                source = await self._protocol.get_current_source()
                if source is not None:
                    if source in self._physical_to_name:
                        custom_name = self._physical_to_name[source]
                        self._current_source = f"{custom_name} ({source})"
                    else:
                        self._current_source = source

                # Audio status queries
                audio_format = await self._protocol.get_audio_format()
                if audio_format:
                    self._audio_format = audio_format

                # Decode mode: query 2ch and MCH separately (1 query each)
                decode_2ch = await self._protocol.get_decode_2ch()
                decode_mch = await self._protocol.get_decode_mch()
                if decode_2ch:
                    self._decode_mode = decode_2ch
                elif decode_mch:
                    self._decode_mode = decode_mch

                sample_rate = await self._protocol.get_sample_rate()
                if sample_rate:
                    self._sample_rate = sample_rate

                direct_mode = await self._protocol.get_direct_mode()
                if direct_mode is not None:
                    self._direct_mode = direct_mode

                # Ready status check
                if self._verify_receiver_stable():
                    if not self._ready:
                        _LOGGER.info("Receiver READY and STABLE")
                    self._ready = True
                    self._power_transition_until = None
                else:
                    self._ready = False

                self._last_successful_poll = datetime.now()
                self.async_write_ha_state()

            except Exception as err:
                _LOGGER.error("Status update error: %s", err, exc_info=True)
                self._ready = False
            finally:
                await self._protocol.disconnect()
                self._last_operation = datetime.now()

    def _verify_receiver_stable(self) -> bool:
        """Verify receiver is in stable operational state.

        Checks multiple parameters to ensure receiver is ready
        for input switching and other commands.

        Returns:
            True if receiver is stable and ready, False otherwise
        """
        if self._state != MediaPlayerState.ON:
            return False

        if self._power_transition_until and datetime.now() < self._power_transition_until:
            # Still in boot sequence
            return False

        # Check relay click timing (should be at least 9s after boot start)
        # This ensures: 6s for relay click + 3s stabilization buffer
        if self._power_transition_until:
            boot_start = self._power_transition_until - timedelta(seconds=10)
            time_since_boot = (datetime.now() - boot_start).total_seconds()
            if time_since_boot < 9:  # 6s relay + 3s stabilization
                _LOGGER.debug("Receiver not stable: only %.1fs since boot (need 9s minimum)", time_since_boot)
                return False

        # Verify we can query receiver successfully (have current data)
        if not self._current_source or self._volume_level is None:
            _LOGGER.debug("Receiver not stable: missing source or volume data")
            return False

        return True

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        return (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the device."""
        return self._state

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        return self._volume_level

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        return self._current_source

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        return self._source_list

    @property
    def is_volume_muted(self) -> bool:
        """Boolean if volume is currently muted."""
        return self._is_volume_muted

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = {
            "ready": self._ready  # Always include ready status
        }
        
        # Connection status tracking
        if self._last_successful_poll:
            time_since = datetime.now() - self._last_successful_poll
            attrs["last_update"] = self._last_successful_poll.strftime("%H:%M:%S")
            attrs["seconds_since_update"] = int(time_since.total_seconds())
            # Connection status indicator
            if time_since.total_seconds() > 120:  # 2 minutes without update
                attrs["connection_status"] = "Stale"
            else:
                attrs["connection_status"] = "OK"
        else:
            attrs["connection_status"] = "Unknown"
        
        # Add integer volume (0-99) for easier use in automations
        if self._volume_level is not None:
            attrs["volume_int"] = int(self._volume_level * 99)
        
        # Audio status
        if self._audio_format:
            attrs["audio_format"] = self._audio_format
        if self._decode_mode:
            attrs["decode_mode"] = self._decode_mode
        if self._sample_rate:
            attrs["sample_rate"] = self._sample_rate
        if self._direct_mode is not None:
            attrs["direct_mode"] = self._direct_mode
            
        return attrs

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        _LOGGER.info("Turning ON Lexicon (via power toggle)")
        
        async def do_power_on():
            """Inner function: actual power on logic."""
            # Set 10s boot timer and optimistic state (relay clicks at ~6s, need stabilization)
            self._power_transition_until = datetime.now() + timedelta(seconds=10)
            self._state = MediaPlayerState.ON
            self._ready = False
            self.async_write_ha_state()
            _LOGGER.debug("Boot timer set for 10 seconds, optimistic state=ON")

            if await self._protocol.power_on():
                _LOGGER.info("Power ON command sent successfully")
                # Schedule poll in 11s (after 10s boot timer + 1s margin) to set ready flag
                self._schedule_next_poll(11)
                return True
            else:
                self._state = MediaPlayerState.OFF
                self._ready = False
                self._power_transition_until = None
                self.async_write_ha_state()
                _LOGGER.error("Failed to turn ON - check connection and RS232 Control setting")
                return False
        
        result = await self._execute_with_connection(do_power_on, "turn_on")
        if not result:
            _LOGGER.error("Power ON failed")

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        _LOGGER.info("Turning OFF Lexicon (via power toggle)")
        
        async def do_power_off():
            """Inner function: actual power off logic."""
            # Set power transition lock for 5 seconds (OFF is faster than ON)
            self._power_transition_until = datetime.now() + timedelta(seconds=5)
            
            if await self._protocol.power_off():
                self._state = MediaPlayerState.OFF
                self._ready = False
                self._volume_level = None
                self._current_source = None
                self.async_write_ha_state()
                _LOGGER.info("Lexicon turned OFF successfully")
                return True
            else:
                # If command failed, clear lock
                self._power_transition_until = None
                _LOGGER.error("Failed to turn OFF - check connection and RS232 Control setting")
                return False
        
        result = await self._execute_with_connection(do_power_off, "turn_off")
        if not result:
            _LOGGER.error("Power OFF failed")

    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        async def do_volume_up():
            """Inner function: actual volume up logic."""
            if await self._protocol.volume_up():
                # Query new volume after short delay
                await asyncio.sleep(0.3)
                volume = await self._protocol.get_volume()
                if volume is not None:
                    self._volume_level = round(volume / 99.0, 2)
                    self.async_write_ha_state()
                return True
            return False
        
        await self._execute_with_connection(do_volume_up, "volume_up")

    async def async_volume_down(self) -> None:
        """Volume down the media player."""
        async def do_volume_down():
            """Inner function: actual volume down logic."""
            if await self._protocol.volume_down():
                # Query new volume after short delay
                await asyncio.sleep(0.3)
                volume = await self._protocol.get_volume()
                if volume is not None:
                    self._volume_level = round(volume / 99.0, 2)
                    self.async_write_ha_state()
                return True
            return False
        
        await self._execute_with_connection(do_volume_down, "volume_down")

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        async def do_set_volume():
            """Inner function: actual set volume logic."""
            # Convert 0.0-1.0 to 0-99
            lexicon_volume = int(volume * 99)
            _LOGGER.debug("Setting volume to %d (%.2f)", lexicon_volume, volume)
            
            if await self._protocol.set_volume(lexicon_volume):
                self._volume_level = round(volume, 2)
                self.async_write_ha_state()
                _LOGGER.info("Volume set to %d", lexicon_volume)
                return True
            else:
                _LOGGER.error("Failed to set volume")
                return False
        
        await self._execute_with_connection(do_set_volume, "set_volume")

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        async def do_mute():
            """Inner function: actual mute logic."""
            if mute:
                if await self._protocol.mute_on():
                    self._is_volume_muted = True
            else:
                if await self._protocol.mute_off():
                    self._is_volume_muted = False
            self.async_write_ha_state()
            return True
        
        await self._execute_with_connection(do_mute, "mute_volume")

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        # STEP 1: Parse source string (BEFORE lock - no connection needed)
        physical_input = None
        
        # Check if format is "Custom (PHYSICAL)"
        if "(" in source and source.endswith(")"):
            # Extract physical name from brackets
            physical_input = source.split("(")[1].rstrip(")")
            _LOGGER.debug("Parsed source: '%s' -> physical: '%s'", source, physical_input)
        elif source in self._name_to_physical:
            # Old format: just custom name
            physical_input = self._name_to_physical[source]
        elif source in LEXICON_INPUTS:
            # Direct physical input name
            physical_input = source
        else:
            _LOGGER.error("Unknown source: %s (available: %s)", source, self._source_list)
            return
        
        # STEP 2: Validate and get RC5 code (BEFORE lock - no connection needed)
        if physical_input not in LEXICON_INPUTS:
            _LOGGER.error("Physical input %s not found in LEXICON_INPUTS", physical_input)
            return
        
        input_code = LEXICON_INPUTS[physical_input]
        _LOGGER.debug("Selecting source %s (physical: %s, code: 0x%02X)", source, physical_input, input_code)
        
        # STEP 3: Execute command with lock (connection required)
        async def do_select_source():
            """Inner function: actual source selection logic."""
            if await self._protocol.select_input(input_code):
                # Wait a moment for receiver to process input change
                await asyncio.sleep(1)
                
                # Query new source immediately and update with correct format
                new_source = await self._protocol.get_current_source()
                if new_source:
                    if new_source in self._physical_to_name:
                        custom_name = self._physical_to_name[new_source]
                        self._current_source = f"{custom_name} ({new_source})"
                    else:
                        self._current_source = new_source
                else:
                    # Assume source changed even if we can't verify
                    self._current_source = source
                
                self.async_write_ha_state()
                _LOGGER.info("Source selected: %s", source)
                return True
            return False
        
        await self._execute_with_connection(do_select_source, "select_source")

    async def async_update(self) -> None:
        """Update the media player state (not used - we poll via timer)."""
        pass
