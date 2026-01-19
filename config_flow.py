"""Config flow for Fellow Aiden."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .fellow_aiden import FellowAiden

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL_MINUTES, MIN_UPDATE_INTERVAL_SECONDS

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
            except Exception:
                # Log with traceback for unexpected errors
                _LOGGER.exception("Error authenticating")
                errors["base"] = "auth"
            else:
                # Set unique_id based on email to prevent duplicate entries
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()

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
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            # Validate update interval
            update_interval_seconds = user_input.get("update_interval_seconds")
            if update_interval_seconds < MIN_UPDATE_INTERVAL_SECONDS:
                errors["update_interval_seconds"] = "too_fast"
            else:
                return self.async_create_entry(title="", data=user_input)

        # Get current values or defaults
        current_interval = self._config_entry.options.get(
            "update_interval_seconds", DEFAULT_UPDATE_INTERVAL_MINUTES * 60
        )

        data_schema = vol.Schema({
            vol.Optional(
                "update_interval_seconds",
                default=current_interval,
                description="Advanced: Update interval in seconds (minimum 30s, default 60s)"
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_UPDATE_INTERVAL_SECONDS, max=300))
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "current_interval": str(current_interval),
                "min_interval": str(MIN_UPDATE_INTERVAL_SECONDS)
            },
            last_step=True,
        )
