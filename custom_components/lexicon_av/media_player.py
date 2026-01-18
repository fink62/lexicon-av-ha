"""Lexicon AV Receiver Media Player entity."""
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_PORT,
    CONF_INPUT_MAPPINGS,
    DEFAULT_PORT,
    DEFAULT_NAME,
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
    _attr_should_poll = False

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
        
        # Build source list from custom names, or physical names if no mapping
        if self._name_to_physical:
            self._source_list = list(self._name_to_physical.keys())
        else:
            self._source_list = list(LEXICON_INPUTS.keys())
        
        self._current_source = None
        self._state = MediaPlayerState.OFF
        self._is_volume_muted = False

        # Set unique ID
        self._attr_unique_id = f"lexicon_av_{protocol._host}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, protocol._host)},
            "name": DEFAULT_NAME,
            "manufacturer": "Lexicon",
            "model": "AV Receiver",
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass - establish initial connection."""
        await super().async_added_to_hass()
        # Try to establish initial connection
        _LOGGER.info("Establishing initial connection to Lexicon...")
        if await self._protocol.connect():
            self._state = MediaPlayerState.IDLE
            _LOGGER.info("Initial connection successful")
        else:
            self._state = MediaPlayerState.OFF
            _LOGGER.warning("Initial connection failed, will retry on first command")

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        await self._protocol.disconnect()
        _LOGGER.info("Entity removed, connection closed")

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        return (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the device."""
        return self._state

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

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        _LOGGER.info("Turning ON Lexicon (via power toggle)")
        if await self._protocol.power_on():
            self._state = MediaPlayerState.ON
            self.async_write_ha_state()
            _LOGGER.info("Lexicon turned ON successfully")
        else:
            _LOGGER.error("Failed to turn ON - check connection and RS232 Control setting")

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        _LOGGER.info("Turning OFF Lexicon (via power toggle)")
        if await self._protocol.power_off():
            self._state = MediaPlayerState.OFF
            self.async_write_ha_state()
            _LOGGER.info("Lexicon turned OFF successfully")
        else:
            _LOGGER.error("Failed to turn OFF - check connection and RS232 Control setting")

    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        await self._protocol.volume_up()

    async def async_volume_down(self) -> None:
        """Volume down the media player."""
        await self._protocol.volume_down()

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
        else:
            _LOGGER.error("Physical input %s not found in LEXICON_INPUTS", physical_input)

    async def async_update(self) -> None:
        """Update the media player state."""
        # The Lexicon doesn't support status polling via RS232
        # State is updated when commands are sent
        pass
