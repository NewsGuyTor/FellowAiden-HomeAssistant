"""Select entity to list brew profiles from Fellow Aiden."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import FellowAidenConfigEntry
from .coordinator import FellowAidenDataUpdateCoordinator
from .base_entity import FellowAidenBaseEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FellowAidenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entity listing all brew profiles."""
    coordinator = entry.runtime_data
    async_add_entities([FellowAidenProfilesSelect(coordinator, entry)], update_before_add=True)


class FellowAidenProfilesSelect(FellowAidenBaseEntity, SelectEntity):
    """Dropdown showing available brew profiles.

    Selecting a profile from the UI is not supported by the Fellow API,
    so async_select_option logs a warning and does nothing. Use the
    schedule or device controls to brew with a specific profile.
    """

    def __init__(self, coordinator: FellowAidenDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}-profile_select"
        self._attr_translation_key = "profiles"

    @property
    def options(self) -> list[str]:
        """Return profile titles."""
        data = self.coordinator.data
        if not data or "profiles" not in data:
            return []
        return [p.get("title", f"Profile {i}") for i, p in enumerate(data["profiles"])]

    @property
    def current_option(self) -> str | None:
        """Return the active profile, or the default, or the first one."""
        data = self.coordinator.data
        if not data or "profiles" not in data or not data["profiles"]:
            return None

        device_config = self.coordinator.data.get("device_config")
        if device_config:
            selected_profile_id = device_config.get("ibSelectedProfileId")
            if selected_profile_id:
                selected_profile = next(
                    (p for p in data["profiles"] if p.get("id") == selected_profile_id),
                    None,
                )
                if selected_profile:
                    return selected_profile.get("title", "Selected Profile")

        default_profile = next(
            (p for p in data["profiles"] if p.get("isDefaultProfile")),
            None,
        )
        if default_profile:
            return default_profile.get("title", "Default Profile")

        return data["profiles"][0].get("title", "Profile 1")

    async def async_select_option(self, option: str) -> None:
        """No-op. The Fellow API doesn't support switching profiles remotely."""
        _LOGGER.warning(
            "Profile selection for '%s' ignored; the Fellow API doesn't support remote profile switching",
            option,
        )
