# binary_sensor.py
import logging
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
    # For baskets & carafe, "presence" was awkward; use None
    ("carafePresent", None, "Carafe Inserted"),
    ("cleaning", BinarySensorDeviceClass.PROBLEM, "Cleaning"),
    ("heaterOn", BinarySensorDeviceClass.HEAT, "Heater On"),
    # We'll interpret DOOR as "True=Open" in HA. So we invert device data:
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
):
    """Set up Fellow Aiden binary sensors."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for key, device_class, name in BINARY_SENSORS:
        entities.append(FellowAidenBinarySensor(coordinator, entry, key, name, device_class))

    async_add_entities(entities)

class FellowAidenBinarySensor(FellowAidenBaseEntity, BinarySensorEntity):
    """Binary sensor for a boolean value from device_config."""

    def __init__(self, coordinator, entry, key, name, device_class):
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        # Modify name to something more natural if you like
        self._attr_name = f"Fellow Aiden {name}"
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """
        Return True if the sensor is active, else False.

        For 'lidClosed', device_class=DOOR => True=Open in HA,
        but the data says 'True=Closed'. We invert it.
        """
        device_config = self.coordinator.data.get("device_config", {})

        raw_value = device_config.get(self._key)

        # If this is the 'lidClosed' key:
        if self._key == "lidClosed":
            # Because DOOR means on=OPEN in Home Assistant
            # and raw_value=True means physically closed => we invert
            return not raw_value

        return raw_value
