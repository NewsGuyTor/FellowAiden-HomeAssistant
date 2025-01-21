"""Config flow for Fellow Aiden."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from fellow_aiden import FellowAiden
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class FellowAidenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fellow Aiden."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        errors = {}
        if user_input is not None:
            email = user_input["email"]
            password = user_input["password"]
            # Try authenticating (blocking) in executor
            try:
                await self.hass.async_add_executor_job(FellowAiden, email, password)
            except Exception as e:
                _LOGGER.error("Error authenticating: %s", e)
                errors["base"] = "auth"
            else:
                # Success, create an entry
                return self.async_create_entry(
                    title=f"Fellow Aiden ({email})",
                    data={
                        "email": email,
                        "password": password
                    },
                )

        data_schema = vol.Schema({
            vol.Required("email"): cv.string,
            vol.Required("password"): cv.string,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FellowAidenOptionsFlowHandler(config_entry)


class FellowAidenOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow if you want user to adjust settings after setup."""

    def __init__(self, config_entry):
        """Initialize."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        # If you have additional configurable options, add them here.
        return self.async_create_entry(title="", data={})
