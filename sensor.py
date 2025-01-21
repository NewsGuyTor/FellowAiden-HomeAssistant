import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FellowAidenDataUpdateCoordinator
from .base_entity import FellowAidenBaseEntity

_LOGGER = logging.getLogger(__name__)

# Standard sensors that pull data from device_config by key
SENSORS = [
    # (key_in_device_config, friendly_name, unit, icon)
    ("chimeVolume", "Chime Volume", None, "mdi:volume-high"),
    ("totalBrewingCycles", "Total Brews", None, "mdi:counter"),
    # We'll interpret totalWaterVolumeL (which is actually ml) and convert to L
    ("totalWaterVolumeL", "Total Water Volume", "L", "mdi:cup-water"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up numeric or text sensors."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Create regular sensors from the SENSORS list
    for key, name, unit, icon in SENSORS:
        entities.append(
            AidenSensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                name=name,
                unit=unit,
                icon=icon
            )
        )

    # Create the derived sensor: Average Water per Brew (liters per brew)
    entities.append(
        AidenAverageWaterPerBrewSensor(
            coordinator=coordinator,
            entry=entry
        )
    )

    async_add_entities(entities, True)


class AidenSensor(FellowAidenBaseEntity, SensorEntity):
    """
    Sensor for numeric or textual data from the device_config.
    If the key is "totalWaterVolumeL", we apply a conversion from ml to L.
    """

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        unit: str | None,
        icon: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        self._attr_name = f"Aiden {name}"
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        device_config = self.coordinator.data.get("device_config", {})
        val = device_config.get(self._key)

        # Convert totalWaterVolumeL from ml to liters if that's the key
        if self._key == "totalWaterVolumeL" and val is not None:
            return round(val / 1000.0, 2)  # Keep 2 decimal places

        return val


class AidenAverageWaterPerBrewSensor(FellowAidenBaseEntity, SensorEntity):
    """
    A derived sensor for average water usage per brew.

    Formula: totalWaterVolume (ml) / totalBrews → convert to liters.
    """

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_name = "Aiden Average Water per Brew"
        self._attr_unique_id = f"{entry.entry_id}-avg_water_per_brew"
        self._attr_icon = "mdi:cup-water"
        self._attr_native_unit_of_measurement = "mL"

    @property
    def native_value(self) -> float | None:
        """Compute average water volume per brew in milliliters (ml)."""
        device_config = self.coordinator.data.get("device_config", {})
        total_water_ml = device_config.get("totalWaterVolumeL")  # Ensure this is in ml
        total_brews = device_config.get("totalBrewingCycles")

        if not total_water_ml or not total_brews or total_brews == 0:
            return None

        # Calculate average in milliliters
        average_ml = total_water_ml / total_brews

        # Optionally, round to the nearest whole number
        return round(average_ml)
