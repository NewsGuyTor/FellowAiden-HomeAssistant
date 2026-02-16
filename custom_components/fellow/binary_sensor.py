"""Binary sensor platform for Fellow Aiden."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import FellowAidenConfigEntry
from .coordinator import FellowAidenDataUpdateCoordinator
from .base_entity import FellowAidenBaseEntity

_LOGGER = logging.getLogger(__name__)

# (api_key, device_class, translation_key)
BINARY_SENSORS = [
    ("brewing", BinarySensorDeviceClass.RUNNING, "brewing"),
    ("carafePresent", None, "carafe_inserted"),
    ("heaterOn", None, "heater"),
    ("lidClosed", BinarySensorDeviceClass.DOOR, "lid"),
    ("missingWater", BinarySensorDeviceClass.PROBLEM, "missing_water"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FellowAidenConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fellow Aiden binary sensors."""
    coordinator = entry.runtime_data

    entities: list[FellowAidenBinarySensor] = []
    for key, device_class, translation_key in BINARY_SENSORS:
        entities.append(
            FellowAidenBinarySensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                translation_key=translation_key,
                device_class=device_class,
            )
        )

    async_add_entities(entities, True)


class FellowAidenBinarySensor(FellowAidenBaseEntity, BinarySensorEntity):
    """Binary sensor for a boolean value from the device config."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        translation_key: str,
        device_class: BinarySensorDeviceClass | None,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """Return True if active.

        For lidClosed the API returns True when the lid is physically
        closed, but HA's DOOR class expects True to mean "open".
        We invert the value for that key.
        """
        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})
        raw_value = device_config.get(self._key)

        if self._key == "lidClosed":
            if raw_value is None:
                return None
            return not raw_value

        return raw_value
