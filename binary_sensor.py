"""Binary sensor platform for Fellow Aiden."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import SensorEntity
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
    ("heaterOn", None, "Heater On"),
    # lidClosed inverts for DOOR logic:
    ("lidClosed", BinarySensorDeviceClass.DOOR, "Lid"),
    ("missingWater", BinarySensorDeviceClass.PROBLEM, "Missing Water"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Fellow Aiden binary sensors and the combined 'Basket' sensor."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    binary_entities: list[FellowAidenBinarySensor] = []
    for key, device_class, name in BINARY_SENSORS:
        binary_entities.append(
            FellowAidenBinarySensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                name=name,
                device_class=device_class
            )
        )

    basket_sensor = AidenBasketSensor(coordinator, entry)

    async_add_entities(binary_entities + [basket_sensor], True)


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
        self._attr_name = f"Aiden {name}"
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """
        Return True if the sensor is active, else False.

        For 'lidClosed' with device_class=DOOR:
          - Home Assistant expects True => Open
          - But the data returns True => physically closed.
          => We invert if key == 'lidClosed'.
        """
        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})
        raw_value = device_config.get(self._key)

        if self._key == "lidClosed":
            # Invert: if lidClosed=True => physically closed => HA expects 'off'
            # Treat None as False (lid open) for safety
            if raw_value is None:
                return None
            return not raw_value

        return raw_value


class AidenBasketSensor(FellowAidenBaseEntity, SensorEntity):
    """
    A text-based sensor that shows whether the brewer has a single brew basket,
    a batch brew basket, or no basket present.
    """

    def __init__(self, coordinator: FellowAidenDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_name = "Aiden Basket"
        self._attr_unique_id = f"{entry.entry_id}-basket"
        self._attr_icon = "mdi:basket"  # or any icon you prefer

    @property
    def native_value(self) -> str:
        """
        Possible states:
          - "Single Serve"
          - "Batch Brew"
          - "Missing"
        """
        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})
        single_basket = device_config.get("singleBrewBasketPresent", False)
        batch_basket = device_config.get("batchBrewBasketPresent", False)

        if single_basket:
            return "Single Serve"
        elif batch_basket:
            return "Batch Brew"
        else:
            return "Missing"
