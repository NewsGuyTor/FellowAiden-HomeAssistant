import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FellowAidenDataUpdateCoordinator
from .base_entity import FellowAidenBaseEntity

_LOGGER = logging.getLogger(__name__)

SENSORS = [
    # (key_in_device_config, friendly_name, native_unit, icon)
    ("chimeVolume", "Chime Volume", None, "mdi:volume-high"),
    # Removed "elevation" since it's now in device info
    ("ibWaterQuantity", "Water Quantity", "ml", "mdi:cup-water"),
    ("totalBrewingCycles", "Total Brewing Cycles", None, "mdi:counter"),
    # Possibly also add isAdvanceMode or something else that might make sense as a sensor
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """Set up numeric or text sensors."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for sensor_info in SENSORS:
        key, name, unit, icon = sensor_info
        entities.append(FellowAidenSensor(coordinator, entry, key, name, unit, icon))

    async_add_entities(entities, True)


class FellowAidenSensor(FellowAidenBaseEntity, SensorEntity):
    """Sensor for numeric or textual data from device_config."""

    def __init__(self, coordinator, entry, key, name, unit, icon):
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        self._attr_name = f"Fellow Aiden {name}"
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self):
        """Return the sensor state."""
        device_config = self.coordinator.data.get("device_config", {})
        return device_config.get(self._key)
