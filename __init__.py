"""Fellow Aiden for Home Assistant."""
from __future__ import annotations

import logging
from datetime import time, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN, PLATFORMS, DEFAULT_PROFILE_TYPE
from .coordinator import FellowAidenDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fellow Aiden from a config entry."""
    _LOGGER.info(f"Setting up Fellow Aiden integration for entry {entry.entry_id}")
    hass.data.setdefault(DOMAIN, {})

    email = entry.data["email"]
    password = entry.data["password"]
    _LOGGER.debug(f"Using email: {email}")

    _LOGGER.debug("Creating coordinator")
    coordinator = FellowAidenDataUpdateCoordinator(hass, entry, email, password)

    _LOGGER.debug("Performing first refresh")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug(f"First refresh completed, data available: {coordinator.data is not None}")

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward platforms (sensor, etc.) and register services
    _LOGGER.debug(f"Forwarding platforms: {PLATFORMS}")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Only register services once, not per config entry
    if not hass.services.has_service(DOMAIN, "create_profile"):
        _LOGGER.debug("Registering services")
        async_register_services(hass)
    else:
        _LOGGER.debug("Services already registered, skipping")

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("Fellow Aiden integration setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options when they change."""
    _LOGGER.debug("Options updated, reloading integration to apply new update interval")
    await hass.config_entries.async_reload(entry.entry_id)


def async_register_services(hass: HomeAssistant) -> None:
    """Register services for creating or deleting profiles."""

    def get_coordinator() -> FellowAidenDataUpdateCoordinator:
        """Get the first available coordinator from hass data."""
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            raise ValueError("No Fellow Aiden integrations configured")

        # Get the first available coordinator
        entry_id = next(iter(domain_data.keys()))
        return domain_data[entry_id]

    def get_profile_id_by_name(profile_name: str) -> str | None:
        """Get profile ID by profile name."""
        coordinator = get_coordinator()
        data = coordinator.data
        if not data or "profiles" not in data:
            return None

        for profile in data["profiles"]:
            if profile.get("title") == profile_name:
                return profile.get("id")
        return None

    def get_available_profile_names() -> list[str]:
        """Get list of available profile names."""
        coordinator = get_coordinator()
        data = coordinator.data
        if not data or "profiles" not in data:
            return []
        return [p.get("title", f"Profile {i}") for i, p in enumerate(data["profiles"])]

    async def async_create_profile(call) -> None:
        """Create a brew profile on the Aiden device."""
        try:
            coordinator = get_coordinator()
            data = {
                "profileType": call.data.get("profileType", DEFAULT_PROFILE_TYPE),
                "title": call.data["title"],
                "ratio": call.data["ratio"],
                "bloomEnabled": call.data["bloomEnabled"],
                "bloomRatio": call.data["bloomRatio"],
                "bloomDuration": call.data["bloomDuration"],
                "bloomTemperature": call.data["bloomTemperature"],
                "ssPulsesEnabled": call.data["ssPulsesEnabled"],
                "ssPulsesNumber": call.data["ssPulsesNumber"],
                "ssPulsesInterval": call.data["ssPulsesInterval"],
                "ssPulseTemperatures": call.data["ssPulseTemperatures"],
                "batchPulsesEnabled": call.data["batchPulsesEnabled"],
                "batchPulsesNumber": call.data["batchPulsesNumber"],
                "batchPulsesInterval": call.data["batchPulsesInterval"],
                "batchPulseTemperatures": call.data["batchPulseTemperatures"],
            }
            _LOGGER.info("Creating profile with data: %s", data)
            await coordinator.async_create_profile(data)
            _LOGGER.info("Profile created successfully")
        except ValueError as e:
            _LOGGER.error("Validation failed when creating profile: %s", e)
            raise ServiceValidationError(str(e))
        except Exception as e:
            _LOGGER.error("Failed to create profile: %s", e)
            raise

    async def async_delete_profile(call) -> None:
        """Delete a brew profile on the Aiden device by ID."""
        try:
            coordinator = get_coordinator()
            pid = call.data.get("profile_id")
            _LOGGER.info("Deleting profile with ID: %s", pid)
            await coordinator.async_delete_profile(pid)
            _LOGGER.info("Profile deleted successfully")
        except Exception as e:
            _LOGGER.error("Failed to delete profile: %s", e)
            raise

    async def async_create_schedule(call) -> None:
        """Create a brew schedule on the Aiden device."""
        try:
            # Handle profile name to ID conversion
            profile_input = call.data.get("profileName", call.data.get("profileId"))
            if not profile_input:
                raise ValueError("Either profileName or profileId must be provided")

            # Try to get profile ID by name first, fall back to direct ID
            profile_id = get_profile_id_by_name(profile_input)
            if not profile_id:
                # Assume it's already an ID - validate format
                import re
                profile_id_regex = re.compile(r'^(p|plocal)\d+$')
                if profile_id_regex.match(profile_input):
                    profile_id = profile_input  # Use the provided ID
                else:
                    available_names = get_available_profile_names()
                    raise ValueError(f"Profile '{profile_input}' not found. Available profiles: {', '.join(available_names)}")

            # Get the time string from the service call
            time_str: str | None = call.data.get("time")
            if not time_str:
                raise ValueError("'time' must be provided for the schedule")

            # Parse the string into a time object
            try:
                time_obj = time.fromisoformat(time_str)
            except ValueError:
                raise ServiceValidationError(f"Invalid time format: '{time_str}'. Please use HH:MM:SS format.")

            seconds_from_start_of_day = (
                time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
            )

            data = {
                "days": [
                    call.data.get("sunday", False),
                    call.data.get("monday", False),
                    call.data.get("tuesday", False),
                    call.data.get("wednesday", False),
                    call.data.get("thursday", False),
                    call.data.get("friday", False),
                    call.data.get("saturday", False),
                ],
                "secondFromStartOfTheDay": seconds_from_start_of_day,
                "enabled": call.data.get("enabled", True),
                "amountOfWater": call.data["amountOfWater"],
                "profileId": profile_id,
            }
            coordinator = get_coordinator()
            _LOGGER.info("Creating schedule with data: %s", data)
            await coordinator.async_create_schedule(data)
            _LOGGER.info("Schedule created successfully")
        except ValueError as e:
            _LOGGER.error("Validation failed when creating schedule: %s", e)
            raise ServiceValidationError(str(e))
        except Exception as e:
            _LOGGER.error("Failed to create schedule: %s", e)
            raise

    async def async_delete_schedule(call) -> None:
        """Delete a brew schedule on the Aiden device by ID."""
        try:
            coordinator = get_coordinator()
            sid = call.data.get("schedule_id")
            _LOGGER.info("Deleting schedule with ID: %s", sid)
            await coordinator.async_delete_schedule(sid)
            _LOGGER.info("Schedule deleted successfully")
        except Exception as e:
            _LOGGER.error("Failed to delete schedule: %s", e)
            raise

    async def async_toggle_schedule(call) -> None:
        """Enable or disable a brew schedule on the Aiden device."""
        try:
            coordinator = get_coordinator()
            sid = call.data.get("schedule_id")
            enabled = call.data.get("enabled", True)
            _LOGGER.info("Toggling schedule %s to enabled=%s", sid, enabled)
            await coordinator.async_toggle_schedule(sid, enabled)
            _LOGGER.info("Schedule toggled successfully")
        except Exception as e:
            _LOGGER.error("Failed to toggle schedule: %s", e)
            raise


    async def async_list_profiles(call) -> ServiceResponse:
        """List all available profiles with names and IDs."""
        coordinator = get_coordinator()
        data = coordinator.data
        if not data or "profiles" not in data or not data["profiles"]:
            _LOGGER.info("No profiles available")
            return {"profiles": []}

        profiles_info = [
            {
                "id": profile.get("id"),
                "title": profile.get("title", "Unnamed Profile"),
                "isDefault": profile.get("isDefaultProfile", False),
            }
            for profile in data["profiles"]
        ]

        _LOGGER.info(f"Returning {len(profiles_info)} profiles as service response.")
        return {"profiles": profiles_info}

    async def async_get_profile_details(call) -> ServiceResponse:
        """Get detailed information about a specific profile."""
        profile_input = call.data.get("profile_name", call.data.get("profile_id"))
        if not profile_input:
            _LOGGER.error("Either profile_name or profile_id must be provided")
            return {"error": "Either profile_name or profile_id must be provided"}

        coordinator = get_coordinator()
        data = coordinator.data
        if not data or "profiles" not in data or not data["profiles"]:
            _LOGGER.error("No profiles available")
            return {"error": "No profiles available"}

        # Find the profile
        target_profile = next(
            (
                profile for profile in data["profiles"]
                if profile.get("title") == profile_input or profile.get("id") == profile_input
            ),
            None,
        )

        if not target_profile:
            available_names = [p.get("title", "Unnamed") for p in data["profiles"]]
            _LOGGER.error(f"Profile '{profile_input}' not found. Available: {', '.join(available_names)}")
            return {"error": f"Profile '{profile_input}' not found"}

        _LOGGER.info(f"Returning details for profile '{target_profile.get('title', 'Unnamed')}'")
        return {"profile": target_profile}

    async def async_debug_water_usage(call) -> ServiceResponse:
        """Debug water usage history by returning all records."""
        _LOGGER.info("=== Returning Water Usage Debug Information ===")
        coordinator = get_coordinator()

        history = coordinator.history_manager._water_usage_history
        device_config = coordinator.data.get("device_config", {})
        current_total = device_config.get("totalWaterVolumeL", 0)

        return {
            "water_usage_history": history,
            "current_device_total_ml": current_total,
            "last_tracked_total_ml": coordinator.history_manager._last_total_water,
        }

    async def async_reset_water_tracking(call) -> None:
        """Reset water usage tracking to current device total."""
        try:
            _LOGGER.info("=== Resetting Water Usage Tracking ===")
            coordinator = get_coordinator()

            # Get current device water total
            device_config = coordinator.data.get("device_config", {})
            current_total = device_config.get("totalWaterVolumeL", 0)

            _LOGGER.info(f"Resetting baseline to current device total: {current_total}ml ({current_total/1000.0:.2f}L)")

            # Reset the tracking
            await coordinator.history_manager.async_reset_water_tracking(current_total)

            _LOGGER.info("Water usage tracking reset complete. Period-specific sensors should now show 0.0L until new usage is detected.")
        except Exception as e:
            _LOGGER.error("Failed to reset water tracking: %s", e)
            raise

    async def async_list_schedules(call) -> ServiceResponse:
        """List all available schedules with their details."""
        try:
            coordinator = get_coordinator()
            # Force a refresh to get latest schedules data
            await coordinator.async_request_refresh()

            data = coordinator.data
            schedules = data.get("schedules", []) if data else []

            _LOGGER.info(f"Returning {len(schedules)} schedules as service response.")
            return {"schedules": schedules}

        except Exception as e:
            _LOGGER.error("Failed to list schedules: %s", e)
            return {"error": f"Failed to list schedules: {e}"}

    async def async_refresh_and_log_data(call) -> ServiceResponse:
        """Manually refresh data and log full API response."""
        try:
            _LOGGER.info("=== Manual Data Refresh Requested ===")
            coordinator = get_coordinator()

            # Force a refresh with verbose logging and get the dictionary response
            data = await hass.async_add_executor_job(coordinator._fetch, True)

            _LOGGER.info("Manual refresh completed - returning full API response.")
            return data
        except Exception as e:
            _LOGGER.error("Failed to refresh and log data: %s", e)
            return {"error": f"Failed to refresh and log data: {e}"}

    hass.services.async_register(
        DOMAIN, "create_profile", async_create_profile, schema=None
    )
    hass.services.async_register(
        DOMAIN, "delete_profile", async_delete_profile, schema=None
    )
    hass.services.async_register(
        DOMAIN, "create_schedule", async_create_schedule, schema=None
    )
    hass.services.async_register(
        DOMAIN, "delete_schedule", async_delete_schedule, schema=None
    )
    hass.services.async_register(
        DOMAIN, "toggle_schedule", async_toggle_schedule, schema=None
    )
    hass.services.async_register(
        DOMAIN,
        "list_profiles",
        async_list_profiles,
        schema=None,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "get_profile_details",
        async_get_profile_details,
        schema=None,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "debug_water_usage",
        async_debug_water_usage,
        schema=None,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "reset_water_tracking", async_reset_water_tracking, schema=None
    )
    hass.services.async_register(
        DOMAIN,
        "list_schedules",
        async_list_schedules,
        schema=None,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "refresh_and_log_data",
        async_refresh_and_log_data,
        schema=None,
        supports_response=SupportsResponse.ONLY,
    )
