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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_INPUT_MAPPINGS,
    DEFAULT_PORT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    LEXICON_INPUTS,
)

# Polling intervals
SCAN_INTERVAL_ON = 30      # 30 seconds when device is on
SCAN_INTERVAL_OFF = 120    # 2 minutes when device is off
SCAN_INTERVAL_STARTUP = 5  # 5 seconds for first few polls after startup
from .lexicon_protocol import LexiconProtocol

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
        if self._name_to_physical:
            self._source_list = list(self._name_to_physical.keys())
        else:
            self._source_list = list(LEXICON_INPUTS.keys())
        
        self._current_source = None
        self._state = MediaPlayerState.OFF
        self._is_volume_muted = False
        self._volume_level = None  # 0.0 - 1.0
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

        # Set unique ID
        self._attr_unique_id = f"lexicon_av_{protocol._host}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, protocol._host)},
            "name": DEFAULT_NAME,
            "manufacturer": "Lexicon",
            "model": "AV Receiver",
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass - establish initial connection and start polling."""
        await super().async_added_to_hass()
        
        # Try to establish initial connection
        _LOGGER.info("Establishing initial connection to Lexicon...")
        if await self._protocol.connect():
            self._state = MediaPlayerState.IDLE
            _LOGGER.info("Initial connection successful")
            
            # Do initial status update
            await self._async_update_status()
        else:
            self._state = MediaPlayerState.OFF
            _LOGGER.warning("Initial connection failed, will retry on first command")
        
        # Start adaptive polling
        await self._schedule_next_poll()
        _LOGGER.info("Adaptive status polling started")

    async def _schedule_next_poll(self):
        """Schedule next poll with adaptive interval based on device state."""
        # Determine interval based on state
        if self._poll_count < 3:
            # First few polls: faster for quick startup
            interval = SCAN_INTERVAL_STARTUP
        elif self._state == MediaPlayerState.ON:
            # Device is on: poll frequently
            interval = SCAN_INTERVAL_ON
        else:
            # Device is off: poll less frequently to save resources
            interval = SCAN_INTERVAL_OFF
        
        _LOGGER.debug("Scheduling next poll in %d seconds (state: %s)", interval, self._state)
        
        # Cancel existing timer if any
        if self._cancel_polling:
            self._cancel_polling()
        
        # Schedule new poll
        self._cancel_polling = async_track_time_interval(
            self.hass,
            self._async_polling_update,
            timedelta(seconds=interval),
        )

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

    async def _async_polling_update(self, now=None) -> None:
        """Periodic status update (called by timer)."""
        self._poll_count += 1
        _LOGGER.debug("Polling update #%d triggered", self._poll_count)
        
        # Store previous state to detect changes
        previous_state = self._state
        
        # Update status
        await self._async_update_status()
        
        # If state changed, reschedule with new interval
        if previous_state != self._state:
            _LOGGER.info("State changed from %s to %s, adjusting poll interval", previous_state, self._state)
            await self._schedule_next_poll()

    async def _async_update_status(self) -> None:
        """Query receiver status and update entity state."""
        try:
            # Query ALL status first, then determine overall state
            
            # Query volume
            volume = await self._protocol.get_volume()
            if volume is not None:
                # Convert 0-99 to 0.0-1.0 and round to 2 decimals
                self._volume_level = round(volume / 99.0, 2)
                _LOGGER.debug("Volume query: %d (%.2f)", volume, self._volume_level)
            else:
                _LOGGER.debug("Volume query returned None")
            
            # Query mute state
            mute = await self._protocol.get_mute_state()
            if mute is not None:
                self._is_volume_muted = mute
                _LOGGER.debug("Mute query: %s", mute)
            else:
                _LOGGER.debug("Mute query returned None")
            
            # Query current source
            source = await self._protocol.get_current_source()
            if source is not None:
                _LOGGER.debug("Source query returned: %s", source)
                # Map physical source to custom name if mapping exists
                if source in self._physical_to_name:
                    self._current_source = self._physical_to_name[source]
                    _LOGGER.debug("Mapped %s -> %s", source, self._current_source)
                else:
                    self._current_source = source
                    _LOGGER.debug("No mapping for %s, using as-is", source)
            else:
                _LOGGER.debug("Source query returned None")
            
            # Query audio status (only when device is on)
            if self._state == MediaPlayerState.ON:
                # Audio format
                audio_format = await self._protocol.get_audio_format()
                if audio_format:
                    self._audio_format = audio_format
                    _LOGGER.debug("Audio format: %s", audio_format)
                
                # Decode mode
                decode_mode = await self._protocol.get_decode_mode()
                if decode_mode:
                    self._decode_mode = decode_mode
                    _LOGGER.debug("Decode mode: %s", decode_mode)
                
                # Sample rate
                sample_rate = await self._protocol.get_sample_rate()
                if sample_rate:
                    self._sample_rate = sample_rate
                    _LOGGER.debug("Sample rate: %s", sample_rate)
                
                # Direct mode
                direct_mode = await self._protocol.get_direct_mode()
                if direct_mode is not None:
                    self._direct_mode = direct_mode
                    _LOGGER.debug("Direct mode: %s", direct_mode)
            
            # Query power state LAST (and determine overall state)
            # BUT: Skip if we're in power transition (to avoid overwriting optimistic state)
            if self._power_transition_until and datetime.now() < self._power_transition_until:
                _LOGGER.debug("Power transition in progress, skipping power state query")
            else:
                # Clear transition lock if expired
                if self._power_transition_until:
                    _LOGGER.debug("Power transition lock expired")
                    self._power_transition_until = None
                
                power_state = await self._protocol.get_power_state()
                if power_state is not None:
                    if power_state:
                        self._state = MediaPlayerState.ON
                        _LOGGER.debug("Power state: ON")
                    else:
                        self._state = MediaPlayerState.OFF
                        _LOGGER.debug("Power state: OFF")
                else:
                    # If we can query volume/source, assume device is on
                    if volume is not None or source is not None:
                        self._state = MediaPlayerState.ON
                        _LOGGER.debug("Power query failed but got volume/source, assuming ON")
                    else:
                        _LOGGER.debug("All queries failed, device might be disconnected")
            
            # Update ready status based on successful queries
            # Ready = device is ON and responding to queries
            if self._state == MediaPlayerState.ON and (volume is not None or source is not None):
                if not self._ready:
                    _LOGGER.info("Receiver is now ready")
                self._ready = True
            else:
                self._ready = False
            
            _LOGGER.debug(
                "Status update complete: power=%s, volume=%s, mute=%s, source=%s, ready=%s",
                self._state, self._volume_level, self._is_volume_muted, self._current_source, self._ready
            )
            
            # Update HA state
            self.async_write_ha_state()
            
        except Exception as err:
            _LOGGER.error("Error during status update: %s", err)

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
        
        if self._audio_format:
            attrs["audio_format"] = self._audio_format
        if self._decode_mode:
            attrs["decode_mode"] = self._decode_mode
        if self._sample_rate:
            attrs["sample_rate"] = self._sample_rate
        if self._direct_mode is not None:
            attrs["direct_mode"] = self._direct_mode
            
        return attrs

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        attrs = {}
        
        # Add integer volume (0-99) for easier use in automations
        if self._volume_level is not None:
            attrs["volume_int"] = int(self._volume_level * 99)
        
        return attrs

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        _LOGGER.info("Turning ON Lexicon (via power toggle)")
        
        # Set power transition lock for 10 seconds
        self._power_transition_until = datetime.now() + timedelta(seconds=10)
        self._state = MediaPlayerState.ON  # Optimistically set to ON
        self._ready = False  # Not ready yet
        self.async_write_ha_state()
        
        if await self._protocol.power_on():
            # Immediate status query after power on
            await self._async_update_status()
            # Mark as ready if we can query volume (means receiver is responding)
            if self._volume_level is not None:
                self._ready = True
                _LOGGER.info("Lexicon turned ON and ready")
            else:
                _LOGGER.info("Lexicon turned ON successfully")
        else:
            # If command failed, clear lock and revert
            self._power_transition_until = None
            self._state = MediaPlayerState.OFF
            self._ready = False
            self.async_write_ha_state()
            _LOGGER.error("Failed to turn ON - check connection and RS232 Control setting")

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        _LOGGER.info("Turning OFF Lexicon (via power toggle)")
        
        # Set power transition lock for 5 seconds (OFF is faster than ON)
        self._power_transition_until = datetime.now() + timedelta(seconds=5)
        
        if await self._protocol.power_off():
            self._state = MediaPlayerState.OFF
            self._ready = False
            self._volume_level = None
            self._current_source = None
            self.async_write_ha_state()
            _LOGGER.info("Lexicon turned OFF successfully")
        else:
            # If command failed, clear lock
            self._power_transition_until = None
            _LOGGER.error("Failed to turn OFF - check connection and RS232 Control setting")

    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        if await self._protocol.volume_up():
            # Query new volume after short delay
            await asyncio.sleep(0.3)
            volume = await self._protocol.get_volume()
            if volume is not None:
                self._volume_level = round(volume / 99.0, 2)
                self.async_write_ha_state()

    async def async_volume_down(self) -> None:
        """Volume down the media player."""
        if await self._protocol.volume_down():
            # Query new volume after short delay
            await asyncio.sleep(0.3)
            volume = await self._protocol.get_volume()
            if volume is not None:
                self._volume_level = round(volume / 99.0, 2)
                self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        # Convert 0.0-1.0 to 0-99
        lexicon_volume = int(volume * 99)
        _LOGGER.debug("Setting volume to %d (%.2f)", lexicon_volume, volume)
        
        if await self._protocol.set_volume(lexicon_volume):
            self._volume_level = round(volume, 2)
            self.async_write_ha_state()
            _LOGGER.info("Volume set to %d", lexicon_volume)
        else:
            _LOGGER.error("Failed to set volume")

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        if mute:
            if await self._protocol.mute_on():
                self._is_volume_muted = True
        else:
            if await self._protocol.mute_off():
                self._is_volume_muted = False
        self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        # Find the physical Lexicon input from the custom name
        physical_input = None
        
        # Check if source is a custom name that maps to a physical input
        if source in self._name_to_physical:
            physical_input = self._name_to_physical[source]
        elif source in LEXICON_INPUTS:
            # Direct physical input name (when no custom mapping used)
            physical_input = source
        else:
            _LOGGER.error("Unknown source: %s (available: %s)", source, self._source_list)
            return
        
        # Get the RC5 code for this physical input
        if physical_input in LEXICON_INPUTS:
            input_code = LEXICON_INPUTS[physical_input]
            _LOGGER.debug("Selecting source %s (physical: %s, code: 0x%02X)", source, physical_input, input_code)
            if await self._protocol.select_input(input_code):
                # Wait a moment for receiver to process input change
                await asyncio.sleep(1)
                
                # Query new source immediately
                new_source = await self._protocol.get_current_source()
                if new_source:
                    if new_source in self._physical_to_name:
                        self._current_source = self._physical_to_name[new_source]
                    else:
                        self._current_source = new_source
                else:
                    # Assume source changed even if we can't verify
                    self._current_source = source
                
                self.async_write_ha_state()
                _LOGGER.info("Source selected: %s", source)
        else:
            _LOGGER.error("Physical input %s not found in LEXICON_INPUTS", physical_input)

    async def async_update(self) -> None:
        """Update the media player state (not used - we poll via timer)."""
        pass
