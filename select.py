"""Select entity to list brew profiles from Fellow Aiden."""
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FellowAidenDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
):
    """Set up select entity listing all brew profiles."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FellowAidenProfilesSelect(coordinator, entry)], True)

class FellowAidenProfilesSelect(CoordinatorEntity, SelectEntity):
    """Select entity that shows all Fellow Aiden brew profiles by title."""

    def __init__(self, coordinator: FellowAidenDataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}-profile_select"
        self._attr_name = "Fellow Aiden Profiles"

    @property
    def options(self) -> list[str]:
        """Return a list of profile titles."""
        data = self.coordinator.data
        if not data or "profiles" not in data:
            return []
        return [p.get("title", f"Profile {i}") for i, p in enumerate(data["profiles"])]

    @property
    def current_option(self) -> str | None:
        """
        Return which profile is considered 'active' (if the device tracks that),
        or a default profile if flagged, otherwise just the first profile.
        """
        data = self.coordinator.data
        if not data or "profiles" not in data or not data["profiles"]:
            return None
        
        # If the device data has 'isDefaultProfile', pick that
        default_profile = next(
            (p for p in data["profiles"] if p.get("isDefaultProfile")), 
            None
        )
        if default_profile:
            return default_profile["title"]

        # Otherwise, just pick the first one
        return data["profiles"][0]["title"]

    async def async_select_option(self, option: str) -> None:
        """
        Called when a user selects a profile from the drop-down.
        This library doesn't have a "set_active_profile" method, so we'll log it only.
        If the library or API eventually supports applying a profile, do it here.
        """
        _LOGGER.info(
            "Selected profile '%s', but there's no method to activate it in the library.",
            option
        )
        # No actual "activate profile" call in the library. 
        # If it existed, we'd do something like:
        # self.coordinator.api.activate_profile(option)
        return
