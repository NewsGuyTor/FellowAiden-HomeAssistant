"""Coordinator to fetch data from the Fellow Aiden cloud."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .fellow_aiden import FellowAiden
from .brew_history import BrewHistoryManager
from .const import DEFAULT_UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

class FellowAidenDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from the Fellow Aiden cloud API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, email: str, password: str) -> None:
        """Initialize with credentials, but do not block the event loop."""
        self.hass = hass
        self.email = email
        self.password = password
        self.api: FellowAiden | None = None
        self.history_manager = BrewHistoryManager(hass, entry.entry_id)
        self._next_refresh_verbose = False

        # Get update interval from options or use default
        update_interval_seconds = entry.options.get(
            "update_interval_seconds", DEFAULT_UPDATE_INTERVAL_MINUTES * 60
        )

        super().__init__(
            hass,
            _LOGGER,
            name="fellow_aiden_coordinator",
            update_interval=timedelta(seconds=update_interval_seconds),
            config_entry=entry,
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Instantiate the library in an executor and do the initial refresh."""
        def create_api() -> FellowAiden:
            return FellowAiden(self.email, self.password)

        self.api = await self.hass.async_add_executor_job(create_api)
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the library asynchronously."""
        _LOGGER.debug("Starting data update cycle")
        if not self.api:
            _LOGGER.error("Fellow Aiden library not initialized")
            raise UpdateFailed("Fellow Aiden library not initialized")

        try:
            _LOGGER.debug("Executing _fetch in executor")
            verbose_logging = self._next_refresh_verbose
            self._next_refresh_verbose = False
            data = await self.hass.async_add_executor_job(self._fetch, verbose_logging)

            # Update historical data with the new data
            _LOGGER.debug("Updating historical data")
            device_config = data.get("device_config", {})
            profiles = data.get("profiles", [])
            await self.history_manager.async_update_data(device_config, profiles)

            _LOGGER.debug("Data update completed successfully")
            return data
        except UpdateFailed:
            # If UpdateFailed was already raised, propagate it
            _LOGGER.error("UpdateFailed exception during data update")
            raise
        except Exception as err:
            _LOGGER.error(f"Unexpected error during data update: {err}")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _fetch(self, verbose_logging: bool = False) -> dict[str, Any]:
        """
        Synchronous call to retrieve brewer info from the library.

        Args:
            verbose_logging: If True, log full API responses. If False, only log basic info.

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
        schedules = self.api.get_schedules()

        if verbose_logging:
            _LOGGER.info("=== Fellow Aiden API Response ===")
            _LOGGER.info(f"Brewer name: {brewer_name}")
            _LOGGER.info(f"Profiles ({len(profiles) if profiles else 0}): {profiles}")
            _LOGGER.info(f"Device config: {device_config}")
            _LOGGER.info(f"Schedules ({len(schedules) if schedules else 0}): {schedules}")
            _LOGGER.info("=== End API Response ===")
        else:
            # Only log summary info during regular polling
            _LOGGER.debug(f"Polled: {len(profiles) if profiles else 0} profiles, {len(schedules) if schedules else 0} schedules, device: {brewer_name}")

        _LOGGER.debug(f"Fetched brewer name: {brewer_name}")
        _LOGGER.debug(f"Fetched profiles: {profiles}")
        _LOGGER.debug(f"Fetched device config: {device_config}")
        _LOGGER.debug(f"Fetched schedules: {schedules}")

        if not brewer_name or not device_config:
            _LOGGER.error("Incomplete data fetched from Fellow Aiden.")
            raise UpdateFailed("Incomplete data fetched from Fellow Aiden.")

        # Historical data will be updated in _async_update_data

        result = {
            "brewer_name": brewer_name,
            "profiles": profiles,
            "device_config": device_config,
            "schedules": schedules,
        }
        _LOGGER.debug(f"Returning data with {len(profiles)} profiles, {len(schedules) if schedules else 0} schedules, and device config keys: {list(device_config.keys()) if device_config else 'None'}")
        return result


    async def async_create_profile(self, profile_data: dict[str, Any]) -> None:
        """Create a new brew profile and refresh coordinator data."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        _LOGGER.info("=== Creating Profile ===")
        _LOGGER.info(f"Profile data: {profile_data}")
        try:
            result = await self.hass.async_add_executor_job(self.api.create_profile, profile_data)
            _LOGGER.info(f"Profile creation result: {result}")
            _LOGGER.info("=== Profile Created Successfully ===")
        except Exception as e:
            _LOGGER.error(f"Profile creation failed: {e}")
            raise
        self._next_refresh_verbose = True
        await self.async_request_refresh()

    async def async_delete_profile(self, profile_id: str) -> None:
        """Delete a brew profile and refresh coordinator data."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        _LOGGER.info("=== Deleting Profile ===")
        _LOGGER.info(f"Profile ID: {profile_id}")
        try:
            result = await self.hass.async_add_executor_job(
                self.api.delete_profile_by_id, profile_id
            )
            _LOGGER.info(f"Profile deletion result: {result}")
            _LOGGER.info("=== Profile Deleted Successfully ===")
        except Exception as e:
            _LOGGER.error(f"Profile deletion failed: {e}")
            raise
        self._next_refresh_verbose = True
        await self.async_request_refresh()

    async def async_create_schedule(self, schedule_data: dict[str, Any]) -> None:
        """Create a new brew schedule and refresh coordinator data."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        _LOGGER.info("=== Creating Schedule ===")
        _LOGGER.info(f"Schedule data: {schedule_data}")
        try:
            result = await self.hass.async_add_executor_job(
                self.api.create_schedule, schedule_data
            )
            _LOGGER.info(f"Schedule creation result: {result}")
            _LOGGER.info("=== Schedule Created Successfully ===")
        except Exception as e:
            _LOGGER.error(f"Schedule creation failed: {e}")
            raise
        self._next_refresh_verbose = True
        await self.async_request_refresh()

    async def async_delete_schedule(self, schedule_id: str) -> None:
        """Delete a brew schedule and refresh coordinator data."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        _LOGGER.info("=== Deleting Schedule ===")
        _LOGGER.info(f"Schedule ID: {schedule_id}")
        try:
            result = await self.hass.async_add_executor_job(
                self.api.delete_schedule_by_id, schedule_id
            )
            _LOGGER.info(f"Schedule deletion result: {result}")
            _LOGGER.info("=== Schedule Deleted Successfully ===")
        except Exception as e:
            _LOGGER.error(f"Schedule deletion failed: {e}")
            raise
        self._next_refresh_verbose = True
        await self.async_request_refresh()

    async def async_toggle_schedule(self, schedule_id: str, enabled: bool) -> None:
        """Enable or disable a brew schedule and refresh coordinator data."""
        if not self.api:
            raise RuntimeError("Fellow Aiden library not initialized")
        _LOGGER.info("=== Toggling Schedule ===")
        _LOGGER.info(f"Schedule ID: {schedule_id}, Enabled: {enabled}")
        try:
            result = await self.hass.async_add_executor_job(
                self.api.toggle_schedule, schedule_id, enabled
            )
            _LOGGER.info(f"Schedule toggle result: {result}")
            _LOGGER.info("=== Schedule Toggled Successfully ===")
        except Exception as e:
            _LOGGER.error(f"Schedule toggle failed: {e}")
            raise
        self._next_refresh_verbose = True
        await self.async_request_refresh()
