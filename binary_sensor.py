"""Binary sensor platform for Fellow Aiden."""
from __future__ import annotations

import logging
from typing import List

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FellowAidenDataUpdateCoordinator
from .base_entity import FellowAidenBaseEntity

_LOGGER = logging.getLogger(__name__)

BINARY_SENSORS = [
    # (key_in_device_config, device_class, friendly_name)
    ("brewing", BinarySensorDeviceClass.RUNNING, "Brewing"),
    ("carafePresent", None, "Carafe Inserted"),
    ("heaterOn", BinarySensorDeviceClass.HEAT, "Heater On"),
    # 'lidClosed' inverts the boolean to match Home Assistant's door sensor logic
    ("lidClosed", BinarySensorDeviceClass.DOOR, "Lid"),
    ("showerHeadPresent", None, "Shower Head Inserted"),
    ("singleBrewBasketPresent", None, "Single Basket Inserted"),
    ("batchBrewBasketPresent", None, "Batch Basket Inserted"),
    ("missingWater", BinarySensorDeviceClass.PROBLEM, "Missing Water"),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Fellow Aiden binary sensors."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: List[FellowAidenBinarySensor] = []
    for key, device_class, name in BINARY_SENSORS:
        entities.append(
            FellowAidenBinarySensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                name=name,
                device_class=device_class
            )
        )

    async_add_entities(entities, True)


class FellowAidenBinarySensor(FellowAidenBaseEntity, BinarySensorEntity):
    """Binary sensor for a boolean value from the device_config."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        device_class: BinarySensorDeviceClass | None
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        self._attr_name = f"Fellow Aiden {name}"
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """
        Return True if the sensor is active, else False.

        For 'lidClosed' with device_class=DOOR: 
        - Home Assistant expects "True => Open" for a DOOR device,
          but our data returns True => physically closed.
        So we invert if key == 'lidClosed'.
        """
        device_config = self.coordinator.data.get("device_config", {})
        raw_value = device_config.get(self._key)

        if self._key == "lidClosed":
            # Invert: if lidClosed=True => physically closed => HA expects 'off'
            return not raw_value

        return raw_value
