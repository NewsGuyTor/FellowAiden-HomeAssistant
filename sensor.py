import logging
from typing import Any
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FellowAidenDataUpdateCoordinator
from .base_entity import FellowAidenBaseEntity

_LOGGER = logging.getLogger(__name__)

# List of standard sensors with their configuration details
STANDARD_SENSORS = [
    # (key_in_device_config, friendly_name, unit, icon)
    ("chimeVolume", "Chime Volume", None, "mdi:volume-high"),
    ("totalBrewingCycles", "Total Brews", None, "mdi:counter"),
    # Convert totalWaterVolumeL (in ml) to liters for display
    ("totalWaterVolumeL", "Total Water Volume", "L", "mdi:cup-water"),
]

# Definitions for brew time-related sensors
BREW_TIME_SENSORS = [
    ("brewStartTime", "Last Brew Start Time", "mdi:clock-start"),
    ("brewEndTime", "Last Brew End Time", "mdi:clock-end"),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors for the Fellow Aiden integration."""
    coordinator: FellowAidenDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Initialize standard sensors
    for key, name, unit, icon in STANDARD_SENSORS:
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

    # Initialize derived sensor: Average Water per Brew
    entities.append(
        AidenAverageWaterPerBrewSensor(
            coordinator=coordinator,
            entry=entry
        )
    )

    # Initialize brew time sensors consecutively for better grouping
    for key, name, icon in BREW_TIME_SENSORS:
        entities.append(
            AidenBrewTimeSensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                name=name,
                icon=icon
            )
        )

    # Initialize the Last Brew Duration sensor immediately after brew time sensors
    entities.append(
        AidenLastBrewDurationSensor(
            coordinator=coordinator,
            entry=entry
        )
    )

    async_add_entities(entities, True)


class AidenSensor(FellowAidenBaseEntity, SensorEntity):
    """
    Represents a sensor for numeric or textual data from the device configuration.
    Applies unit conversions when necessary.
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
        """Initialize the sensor with provided configuration."""
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        self._attr_name = f"Aiden {name}"
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self) -> Any:
        """Retrieve and process the sensor's value."""
        device_config = self.coordinator.data.get("device_config", {})
        value = device_config.get(self._key)

        # Apply unit conversion for water volume if applicable
        if self._key == "totalWaterVolumeL" and value is not None:
            return round(value / 1000.0, 2)  # Convert ml to liters

        return value


class AidenAverageWaterPerBrewSensor(FellowAidenBaseEntity, SensorEntity):
    """
    Calculates the average water usage per brew cycle.
    Formula: totalWaterVolume (ml) / totalBrewingCycles → milliliters per brew.
    """

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the average water per brew sensor."""
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_name = "Aiden Average Water per Brew"
        self._attr_unique_id = f"{entry.entry_id}-avg_water_per_brew"
        self._attr_icon = "mdi:cup-water"
        self._attr_native_unit_of_measurement = "mL"

    @property
    def native_value(self) -> float | None:
        """Compute and return the average water volume per brew."""
        device_config = self.coordinator.data.get("device_config", {})
        total_water_ml = device_config.get("totalWaterVolumeL")
        total_brews = device_config.get("totalBrewingCycles")

        if not total_water_ml or not total_brews or total_brews == 0:
            return None

        average_ml = total_water_ml / total_brews
        return round(average_ml)


class AidenBrewTimeSensor(FellowAidenBaseEntity, SensorEntity):
    """
    Displays the last brew start or end time.
    Converts Unix timestamps to human-readable datetime strings.
    """

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the brew time sensor."""
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key  # 'brewStartTime' or 'brewEndTime'
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = None  # Time represented as a string

    @property
    def native_value(self) -> str | None:
        """Convert and return the brew time as a formatted datetime string."""
        device_config = self.coordinator.data.get("device_config", {})
        timestamp_str = device_config.get(self._key)

        if not timestamp_str or timestamp_str == "0":
            return None

        try:
            # Convert the timestamp string to an integer
            timestamp_int = int(timestamp_str)
            # Avoid epoch time
            if timestamp_int == 0:
                return None
            # Convert Unix timestamp to a datetime object
            brew_datetime = datetime.fromtimestamp(timestamp_int)
            # Validate timestamp (e.g., after year 2023)
            if brew_datetime.year < 2023:
                return None
            # Format datetime for display (ISO8601 format)
            return brew_datetime.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as error:
            _LOGGER.error(f"Error parsing {self._key}: {error}")
            return None


class AidenLastBrewDurationSensor(FellowAidenBaseEntity, SensorEntity):
    """
    Calculates the duration of the last brew cycle in seconds.
    Derived from the difference between brew end and start times.
    """

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the last brew duration sensor."""
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_name = "Aiden Last Brew Duration"
        self._attr_unique_id = f"{entry.entry_id}-last_brew_duration"
        self._attr_icon = "mdi:timer-outline"
        self._attr_native_unit_of_measurement = "seconds"

    @property
    def native_value(self) -> int | None:
        """Compute and return the duration of the last brew cycle."""
        device_config = self.coordinator.data.get("device_config", {})
        start_time_str = device_config.get("brewStartTime")
        end_time_str = device_config.get("brewEndTime")

        if not start_time_str or not end_time_str:
            return None

        try:
            start_timestamp = int(start_time_str)
            end_timestamp = int(end_time_str)

            # Validate timestamps to avoid negative durations or epoch times
            if start_timestamp == 0 or end_timestamp == 0:
                return None
            if start_timestamp < 1704067201:  # Timestamp before 2024-01-01
                return None
            if end_timestamp < 1704067201:
                return None

            duration = end_timestamp - start_timestamp

            if duration < 0:
                _LOGGER.warning("End time precedes start time for the last brew cycle.")
                return None

            return duration
        except (ValueError, TypeError) as error:
            _LOGGER.error(f"Error calculating brew duration: {error}")
            return None
