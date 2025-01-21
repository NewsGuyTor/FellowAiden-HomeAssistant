"""Coordinator to fetch data from the Fellow Aiden cloud."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from fellow_aiden import FellowAiden

_LOGGER = logging.getLogger(__name__)

class FellowAidenDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from the Fellow Aiden cloud API."""

    def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
        """Initialize with credentials, but do not block the event loop."""
        self.hass = hass
        self.email = email
        self.password = password
        self.api: FellowAiden | None = None

        super().__init__(
            hass,
            _LOGGER,
            name="fellow_aiden_coordinator",
            update_interval=timedelta(minutes=1),
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Instantiate the library in an executor and do the initial refresh."""
        def create_api() -> FellowAiden:
            return FellowAiden(self.email, self.password)

        self.api = await self.hass.async_add_executor_job(create_api)
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the library asynchronously."""
        if not self.api:
            raise UpdateFailed("Fellow Aiden library not initialized")

        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except Exception as err:
            raise UpdateFailed(f"Error updating data: {err}") from err

    def _fetch(self) -> dict[str, Any]:
        """Synchronous call to retrieve brewer info from the library."""
        brewer_name = self.api.get_display_name()
        profiles = self.api.get_profiles()
        # Access the device_config from the library
        device_config = self.api._device_config  # or a formal getter if available

        return {
            "brewer_name": brewer_name,
            "profiles": profiles,
            "device_config": device_config,  # includes firmware, IP, MAC, SSID, etc.
        }

    def create_profile(self, profile_data: dict[str, Any]) -> None:
        """Create a new brew profile."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        self.api.create_profile(profile_data)
        self._fetch()  # Refresh internal data (if needed, consider a forced coordinator update)

    def delete_profile(self, profile_id: str) -> None:
        """Delete a brew profile."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        self.api.delete_profile_by_id(profile_id)
        self._fetch()  # Refresh internal data (same note as above)
