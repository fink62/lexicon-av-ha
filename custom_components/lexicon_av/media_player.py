"""Lexicon AV Receiver Media Player entity."""
import asyncio
import logging
from datetime import timedelta

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
        
        # Start polling timer (every 30 seconds)
        self._cancel_polling = async_track_time_interval(
            self.hass,
            self._async_polling_update,
            timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        _LOGGER.info("Status polling started (interval: %ds)", DEFAULT_SCAN_INTERVAL)

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
        _LOGGER.debug("Polling update triggered")
        await self._async_update_status()

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
            
            # Query power state LAST (and determine overall state)
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
            
            _LOGGER.debug(
                "Status update complete: power=%s, volume=%s, mute=%s, source=%s",
                self._state, self._volume_level, self._is_volume_muted, self._current_source
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
        """Return entity specific state attributes."""
        attrs = {}
        
        # Add integer volume (0-99) for easier use in automations
        if self._volume_level is not None:
            attrs["volume_int"] = int(self._volume_level * 99)
        
        return attrs

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        _LOGGER.info("Turning ON Lexicon (via power toggle)")
        if await self._protocol.power_on():
            self._state = MediaPlayerState.ON
            # Wait a bit for receiver to power on, then query status
            await asyncio.sleep(2)
            await self._async_update_status()
            _LOGGER.info("Lexicon turned ON successfully")
        else:
            _LOGGER.error("Failed to turn ON - check connection and RS232 Control setting")

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        _LOGGER.info("Turning OFF Lexicon (via power toggle)")
        if await self._protocol.power_off():
            self._state = MediaPlayerState.OFF
            self._volume_level = None
            self._current_source = None
            self.async_write_ha_state()
            _LOGGER.info("Lexicon turned OFF successfully")
        else:
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
                self._current_source = source
                self.async_write_ha_state()
                _LOGGER.info("Source selected: %s", source)
        else:
            _LOGGER.error("Physical input %s not found in LEXICON_INPUTS", physical_input)

    async def async_update(self) -> None:
        """Update the media player state (not used - we poll via timer)."""
        pass
