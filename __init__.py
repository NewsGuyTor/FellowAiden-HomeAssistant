"""Fellow Aiden for Home Assistant."""
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
    # Instantiate the library & do the initial refresh (in executor)
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
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def async_register_services(hass: HomeAssistant, coordinator: FellowAidenDataUpdateCoordinator, entry: ConfigEntry) -> None:
    """Register services for creating or deleting profiles."""

    async def async_create_profile(call):
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

    async def async_delete_profile(call):
        """Delete a brew profile on the Aiden device by ID."""
        pid = call.data.get("profile_id")
        await hass.async_add_executor_job(coordinator.delete_profile, pid)

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
