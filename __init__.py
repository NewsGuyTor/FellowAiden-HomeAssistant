"""Fellow Aiden for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import FellowAidenDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fellow Aiden from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data["email"]
    password = entry.data["password"]

    coordinator = FellowAidenDataUpdateCoordinator(hass, email, password)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward platforms (sensor, etc.) and register services
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass, coordinator, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def async_register_services(
    hass: HomeAssistant,
    coordinator: FellowAidenDataUpdateCoordinator,
    entry: ConfigEntry
) -> None:
    """Register services for creating or deleting profiles."""

    def get_profile_id_by_name(profile_name: str) -> str | None:
        """Get profile ID by profile name."""
        data = coordinator.data
        if not data or "profiles" not in data:
            return None
        
        for profile in data["profiles"]:
            if profile.get("title") == profile_name:
                return profile.get("id")
        return None

    def get_available_profile_names() -> list[str]:
        """Get list of available profile names."""
        data = coordinator.data
        if not data or "profiles" not in data:
            return []
        return [p.get("title", f"Profile {i}") for i, p in enumerate(data["profiles"])]

    async def async_create_profile(call) -> None:
        """Create a brew profile on the Aiden device."""
        data = {
            "profileType": call.data.get("profileType", 0),
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
        await hass.async_add_executor_job(coordinator.create_profile, data)

    async def async_delete_profile(call) -> None:
        """Delete a brew profile on the Aiden device by ID."""
        pid = call.data.get("profile_id")
        await hass.async_add_executor_job(coordinator.delete_profile, pid)

    async def async_create_schedule(call) -> None:
        """Create a brew schedule on the Aiden device."""
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
            "secondFromStartOfTheDay": call.data["secondFromStartOfTheDay"],
            "enabled": call.data.get("enabled", True),
            "amountOfWater": call.data["amountOfWater"],
            "profileId": profile_id,
        }
        await hass.async_add_executor_job(coordinator.create_schedule, data)

    async def async_delete_schedule(call) -> None:
        """Delete a brew schedule on the Aiden device by ID."""
        sid = call.data.get("schedule_id")
        await hass.async_add_executor_job(coordinator.delete_schedule, sid)

    async def async_toggle_schedule(call) -> None:
        """Enable or disable a brew schedule on the Aiden device."""
        sid = call.data.get("schedule_id")
        enabled = call.data.get("enabled", True)
        await hass.async_add_executor_job(coordinator.toggle_schedule, sid, enabled)

    async def async_start_brew(call) -> None:
        """Start an immediate brew on the Aiden device."""
        # Handle profile name to ID conversion
        profile_input = call.data.get("profileName", call.data.get("profile_id"))
        profile_id = None
        
        if profile_input:
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
        
        water_amount = call.data.get("water_amount")
        await hass.async_add_executor_job(coordinator.start_brew, profile_id, water_amount)

    hass.services.async_register(
        DOMAIN,
        "create_profile",
        async_create_profile,
        schema=None
    )
    hass.services.async_register(
        DOMAIN,
        "delete_profile",
        async_delete_profile,
        schema=None
    )
    hass.services.async_register(
        DOMAIN,
        "create_schedule",
        async_create_schedule,
        schema=None
    )
    hass.services.async_register(
        DOMAIN,
        "delete_schedule",
        async_delete_schedule,
        schema=None
    )
    hass.services.async_register(
        DOMAIN,
        "toggle_schedule",
        async_toggle_schedule,
        schema=None
    )
    hass.services.async_register(
        DOMAIN,
        "start_brew",
        async_start_brew,
        schema=None
    )
