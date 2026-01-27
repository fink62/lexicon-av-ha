"""Config flow for Lexicon AV Receiver integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

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


async def validate_connection(hass: HomeAssistant, host: str, port: int) -> bool:
    """Validate the connection to the Lexicon receiver."""
    protocol = LexiconProtocol(host, port)
    try:
        return await protocol.connect()
    finally:
        await protocol.disconnect()


class LexiconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lexicon AV Receiver."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate connection
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            if await validate_connection(self.hass, host, port):
                # Create unique ID
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()

                # Move to input mapping step
                self.context["user_data"] = user_input
                return await self.async_step_input_mapping()
            else:
                errors["base"] = "cannot_connect"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
            }),
            errors=errors,
        )

    async def async_step_input_mapping(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure input mappings."""
        if user_input is not None:
            # Combine with previous data
            data = self.context["user_data"]
            data[CONF_INPUT_MAPPINGS] = user_input

            return self.async_create_entry(
                title=DEFAULT_NAME,
                data=data,
            )

        # Build schema with all available Lexicon inputs
        schema_dict = {}
        for input_name in LEXICON_INPUTS:
            schema_dict[vol.Optional(input_name)] = str

        return self.async_show_form(
            step_id="input_mapping",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "inputs": ", ".join(LEXICON_INPUTS.keys())
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return LexiconOptionsFlowHandler()


class LexiconOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Lexicon options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Separate connection settings from input mappings
            new_host = user_input.pop(CONF_HOST)
            new_port = user_input.pop(CONF_PORT)

            old_host = self.config_entry.data.get(CONF_HOST)
            old_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)

            # Validate connection if host or port changed
            if new_host != old_host or new_port != old_port:
                if not await validate_connection(self.hass, new_host, new_port):
                    errors["base"] = "cannot_connect"

            if not errors:
                new_data = {
                    CONF_HOST: new_host,
                    CONF_PORT: new_port,
                    CONF_INPUT_MAPPINGS: user_input,
                }

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=new_data,
                    unique_id=f"{new_host}:{new_port}",
                )

                # Reload the integration to apply changes
                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )

                return self.async_create_entry(title="", data={})

        # Get current values
        current_host = self.config_entry.data.get(CONF_HOST, "")
        current_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        current_mappings = self.config_entry.data.get(CONF_INPUT_MAPPINGS, {})

        # Build schema with current values as defaults
        schema_dict = {
            vol.Required(CONF_HOST, default=current_host): str,
            vol.Optional(CONF_PORT, default=current_port): cv.port,
        }
        for input_name in LEXICON_INPUTS:
            default = current_mappings.get(input_name, "")
            schema_dict[vol.Optional(input_name, default=default)] = str

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
