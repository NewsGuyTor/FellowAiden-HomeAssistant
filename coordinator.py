"""Coordinator to fetch data from the Fellow Aiden cloud."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .fellow_aiden import FellowAiden

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
        except UpdateFailed:
            # If UpdateFailed was already raised, propagate it
            raise
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _fetch(self) -> dict[str, Any]:
        """
        Synchronous call to retrieve brewer info from the library.

        HACK:
        We call the private method __device() to re-fetch the device data
        from the cloud. This is not ideal, but works until the library
        provides a public refresh() method.
        """
        # Forcing a re-download of device info from the cloud:
        try:
            _LOGGER.debug("Attempting to fetch device data.")
            self.api._FellowAiden__device()  # <-- HACK: Accessing private method
        except Exception as e:
            _LOGGER.error(f"Error fetching device data: {e}. Attempting to re-authenticate.")
            try:
                _LOGGER.debug("Re-authenticating user.")
                self.api._FellowAiden__auth()  # <-- HACK: Accessing private method
                _LOGGER.debug("Re-authentication successful. Re-fetching device data.")
                self.api._FellowAiden__device()  # <-- HACK: Accessing private method
            except Exception as auth_e:
                _LOGGER.error(f"Re-authentication failed: {auth_e}")
                raise UpdateFailed(f"Error updating data: {auth_e}") from auth_e

        brewer_name = self.api.get_display_name()
        profiles = self.api.get_profiles()
        device_config = self.api.get_device_config()

        _LOGGER.debug(f"Fetched brewer name: {brewer_name}")
        _LOGGER.debug(f"Fetched profiles: {profiles}")
        _LOGGER.debug(f"Fetched device config: {device_config}")

        if not brewer_name or not device_config:
            _LOGGER.error("Incomplete data fetched from Fellow Aiden.")
            raise UpdateFailed("Incomplete data fetched from Fellow Aiden.")

        return {
            "brewer_name": brewer_name,
            "profiles": profiles,
            "device_config": device_config,
        }


    def create_profile(self, profile_data: dict[str, Any]) -> None:
        """Create a new brew profile."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        self.api.create_profile(profile_data)
        self._fetch()  # Refresh internal data

    def delete_profile(self, profile_id: str) -> None:
        """Delete a brew profile."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        self.api.delete_profile_by_id(profile_id)
        self._fetch()  # Refresh internal data

    def create_schedule(self, schedule_data: dict[str, Any]) -> None:
        """Create a new brew schedule."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        self.api.create_schedule(schedule_data)
        self._fetch()  # Refresh internal data

    def delete_schedule(self, schedule_id: str) -> None:
        """Delete a brew schedule."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        self.api.delete_schedule_by_id(schedule_id)
        self._fetch()  # Refresh internal data

    def toggle_schedule(self, schedule_id: str, enabled: bool) -> None:
        """Enable or disable a brew schedule."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        self.api.toggle_schedule(schedule_id, enabled)
        self._fetch()  # Refresh internal data

    def start_brew(self, profile_id: str, water_amount: int = None) -> None:
        """Start a brew by creating a temporary schedule 1 minute in the future."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        
        try:
            # Calculate time 1 minute from now
            from datetime import datetime, timedelta
            now = datetime.now()
            brew_time = now + timedelta(minutes=1)
            seconds_from_start_of_day = (brew_time.hour * 3600 + 
                                       brew_time.minute * 60 + 
                                       brew_time.second)
            
            # Use default water amount if not specified
            if not water_amount:
                water_amount = 420  # Default 420ml
            
            # Create a temporary schedule for today only
            weekday = brew_time.weekday()  # 0=Monday, 6=Sunday
            days = [False] * 7  # Sunday first for API
            
            # Convert weekday to Sunday-first format (API expects Sunday=0)
            if weekday == 6:  # Sunday
                days[0] = True
            else:  # Monday=1, Tuesday=2, etc.
                days[weekday + 1] = True
            
            schedule_data = {
                "days": days,
                "secondFromStartOfTheDay": seconds_from_start_of_day,
                "enabled": True,
                "amountOfWater": water_amount,
                "profileId": profile_id,
            }
            
            _LOGGER.info(f"Creating temporary brew schedule for {brew_time.strftime('%H:%M:%S')} with profile {profile_id}")
            self.api.create_schedule(schedule_data)
            self._fetch()  # Refresh internal data
            
        except Exception as e:
            _LOGGER.error(f"Failed to start brew: {e}")
            raise RuntimeError(f"Failed to start brew: {e}") from e
