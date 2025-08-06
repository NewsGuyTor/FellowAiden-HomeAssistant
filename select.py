"""Select entity to list brew profiles from Fellow Aiden."""
from __future__ import annotations

import logging
from typing import List

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
) -> None:
    """Set up select entity listing all brew profiles."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FellowAidenProfilesSelect(coordinator, entry)], True)


class FellowAidenProfilesSelect(CoordinatorEntity, SelectEntity):
    """Select entity that shows all Fellow Aiden brew profiles by title."""

    def __init__(self, coordinator: FellowAidenDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}-profile_select"
        self._attr_name = "Fellow Aiden Profiles"

    @property
    def options(self) -> List[str]:
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
        Currently disabled - use services to manage profiles instead.
        """
        _LOGGER.info("Profile selection attempted for '%s', but this feature is disabled", option)
        _LOGGER.info("Use the fellow.start_brew service with profileName parameter instead")
        # Note: This method is required by Home Assistant but we don't implement profile switching
        # Users should use the fellow.start_brew service to brew with specific profiles
