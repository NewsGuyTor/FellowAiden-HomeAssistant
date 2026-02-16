import logging
from typing import Any
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TIMESTAMP_2024_01_01, MIN_VALID_YEAR, MIN_HISTORICAL_DATA_FOR_ACCURACY, FellowAidenConfigEntry
from .coordinator import FellowAidenDataUpdateCoordinator
from .base_entity import FellowAidenBaseEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# Standard sensors: (api_key, translation_key, unit, icon)
STANDARD_SENSORS = [
    ("chimeVolume", "chime_volume", None, "mdi:volume-high"),
    ("totalBrewingCycles", "total_brews", None, "mdi:counter"),
    ("totalWaterVolumeL", "total_water_volume", "L", "mdi:cup-water"),
    ("brewingWaterVolumeMl", "last_brew_volume", "mL", "mdi:coffee-outline"),
]

# Brew time sensors: (api_key, translation_key, icon)
BREW_TIME_SENSORS = [
    ("brewStartTime", "last_brew_start_time", "mdi:clock-start"),
    ("brewEndTime", "last_brew_end_time", "mdi:clock-end"),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: FellowAidenConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors for the Fellow Aiden integration."""
    _LOGGER.debug("Setting up sensors for entry %s", entry.entry_id)
    coordinator = entry.runtime_data

    _LOGGER.debug("Coordinator data available: %s", coordinator.data is not None)
    if coordinator.data:
        _LOGGER.debug("Coordinator data keys: %s", list(coordinator.data.keys()))

    entities: list[SensorEntity] = []

    # Standard sensors from device config
    for key, translation_key, unit, icon in STANDARD_SENSORS:
        entities.append(
            AidenSensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                translation_key=translation_key,
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

    # Brew time sensors
    for key, translation_key, icon in BREW_TIME_SENSORS:
        entities.append(
            AidenBrewTimeSensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                translation_key=translation_key,
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

    # Analytics sensors
    entities.extend([
        AidenAverageTimeBetweenBrewsSensor(coordinator, entry),
        AidenLastBrewTimeSensor(coordinator, entry),
        AidenTotalWaterTodaySensor(coordinator, entry),
        AidenTotalWaterWeekSensor(coordinator, entry),
        AidenTotalWaterMonthSensor(coordinator, entry),
        AidenAverageBrewDurationSensor(coordinator, entry),
        AidenMostPopularProfileSensor(coordinator, entry),
        AidenCurrentProfileSensor(coordinator, entry),
        AidenBasketSensor(coordinator, entry),
    ])

    _LOGGER.debug("Adding %d sensor entities", len(entities))
    async_add_entities(entities, update_before_add=True)
    _LOGGER.info("Successfully set up %d sensors for Fellow Aiden", len(entities))


class AidenSensor(FellowAidenBaseEntity, SensorEntity):
    """Sensor for a value read directly from the device config."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        translation_key: str,
        unit: str | None,
        icon: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        self._attr_translation_key = translation_key
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
    """Average water usage per brew: totalWaterVolume / totalBrewingCycles."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "average_water_per_brew"
        self._attr_unique_id = f"{entry.entry_id}-avg_water_per_brew"
        self._attr_icon = "mdi:cup-water"
        self._attr_native_unit_of_measurement = "mL"

    @property
    def native_value(self) -> float | None:
        """Compute and return the average water volume per brew."""
        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})
        total_water_ml = device_config.get("totalWaterVolumeL")
        total_brews = device_config.get("totalBrewingCycles")

        # Use explicit None checks - 0 is a valid value for total_water_ml
        if total_water_ml is None or total_brews is None or total_brews == 0:
            return None

        average_ml = total_water_ml / total_brews
        return round(average_ml)


class AidenBrewTimeSensor(FellowAidenBaseEntity, SensorEntity):
    """Displays a brew start or end time, converted from a Unix timestamp."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        translation_key: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.entry_id}-{key}"
        self._attr_icon = icon

    @property
    def native_value(self) -> str | None:
        """Convert and return the brew time as a formatted datetime string."""
        from homeassistant.util import dt as dt_util

        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})
        timestamp_str = device_config.get(self._key)

        if not timestamp_str or timestamp_str == "0":
            return None

        try:
            # Convert the timestamp string to an integer
            timestamp_int = int(timestamp_str)
            # Avoid epoch time
            if timestamp_int == 0:
                return None
            # Convert Unix timestamp to a timezone-aware datetime object
            brew_datetime = dt_util.as_local(dt_util.utc_from_timestamp(timestamp_int))
            # Validate timestamp (e.g., after minimum valid year)
            if brew_datetime.year < MIN_VALID_YEAR:
                return None
            # Format datetime for display (ISO8601 format)
            return brew_datetime.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, OSError, OverflowError) as error:
            _LOGGER.error("Error parsing %s: %s", self._key, error)
            return None


class AidenLastBrewDurationSensor(FellowAidenBaseEntity, SensorEntity):
    """Duration of the last brew, derived from end minus start timestamps."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "last_brew_duration"
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
            if start_timestamp < TIMESTAMP_2024_01_01:  # Timestamp before 2024-01-01
                return None
            if end_timestamp < TIMESTAMP_2024_01_01:
                return None

            duration = end_timestamp - start_timestamp

            if duration < 0:
                _LOGGER.warning("End time precedes start time for the last brew cycle.")
                return None

            return duration
        except (ValueError, TypeError) as error:
            _LOGGER.error("Error calculating brew duration: %s", error)
            return None


class AidenAverageTimeBetweenBrewsSensor(FellowAidenBaseEntity, SensorEntity):
    """Rough estimate of average time between brews, from historical data."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "average_time_between_brews"
        self._attr_unique_id = f"{entry.entry_id}-avg_time_between_brews"
        self._attr_icon = "mdi:clock-outline"
        self._attr_native_unit_of_measurement = "hours"

    @property
    def native_value(self) -> float | None:
        """Calculate average time between brews using historical data."""
        return self.coordinator.history_manager.get_average_time_between_brews()

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        history_count = self.coordinator.history_manager.get_brew_history_count()
        return {
            "historical_brews": history_count,
            "accuracy": "High - based on actual historical data" if history_count >= MIN_HISTORICAL_DATA_FOR_ACCURACY else "Low - insufficient historical data",
            "note": f"Calculated from {history_count} recorded brews"
        }


class AidenLastBrewTimeSensor(FellowAidenBaseEntity, SensorEntity):
    """When the last brew finished (timestamp)."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "last_brew_time"
        self._attr_unique_id = f"{entry.entry_id}-last_brew_time"
        self._attr_icon = "mdi:coffee-outline"
        self._attr_device_class = "timestamp"

    @property
    def native_value(self) -> datetime | None:
        """Return the last brew completion time using historical data."""
        from homeassistant.util import dt as dt_util
        
        # Try historical data first, fallback to device data
        historical_time = self.coordinator.history_manager.get_last_brew_time()
        if historical_time:
            # Ensure timezone is set
            if historical_time.tzinfo is None:
                return dt_util.as_local(historical_time)
            return historical_time
            
        # Fallback to device data
        device_config = self.coordinator.data.get("device_config", {})
        end_time_str = device_config.get("brewEndTime")

        if not end_time_str or end_time_str == "0":
            return None

        try:
            timestamp_int = int(end_time_str)
            if timestamp_int == 0 or timestamp_int < TIMESTAMP_2024_01_01:  # Before 2024
                return None
            # Create timezone-aware datetime
            return dt_util.utc_from_timestamp(timestamp_int)
        except (ValueError, TypeError) as error:
            _LOGGER.error("Error parsing last brew time: %s", error)
            return None


class AidenTotalWaterTodaySensor(FellowAidenBaseEntity, SensorEntity):
    """Water used today, from historical tracking data."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "total_water_today"
        self._attr_unique_id = f"{entry.entry_id}-total_water_today"
        self._attr_icon = "mdi:water"
        self._attr_native_unit_of_measurement = "L"

    @property
    def native_value(self) -> float | None:
        """Return total water used today using historical data."""
        # IMPORTANT: Only use historical tracking data, never fallback to device totals
        water_usage = self.coordinator.history_manager.get_water_usage_for_period(1)
        _LOGGER.debug(f"Water usage today from history: {water_usage}L")
        
        # Ensure we never accidentally return device lifetime totals
        if water_usage is None or water_usage < 0:
            _LOGGER.warning("Invalid water usage value from history manager, returning 0.0")
            return 0.0
            
        return water_usage

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        water_records = self.coordinator.history_manager.get_water_usage_count()
        return {
            "historical_records": water_records,
            "accuracy": "High - based on actual usage tracking" if water_records > 0 else "Low - no historical data yet",
            "note": f"Calculated from {water_records} water usage records"
        }


class AidenTotalWaterWeekSensor(FellowAidenBaseEntity, SensorEntity):
    """Water used this week, from historical tracking data."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "total_water_this_week"
        self._attr_unique_id = f"{entry.entry_id}-total_water_week"
        self._attr_icon = "mdi:water"
        self._attr_native_unit_of_measurement = "L"

    @property
    def native_value(self) -> float | None:
        """Return total water used this week using historical data."""
        # IMPORTANT: Only use historical tracking data, never fallback to device totals
        water_usage = self.coordinator.history_manager.get_water_usage_for_period(7)
        _LOGGER.debug(f"Water usage this week from history: {water_usage}L")
        
        # Ensure we never accidentally return device lifetime totals
        if water_usage is None or water_usage < 0:
            _LOGGER.warning("Invalid water usage value from history manager, returning 0.0")
            return 0.0
            
        return water_usage

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        water_records = self.coordinator.history_manager.get_water_usage_count()
        brew_count = self.coordinator.history_manager.get_brew_count_for_period(7)
        return {
            "historical_records": water_records,
            "brews_this_week": brew_count,
            "accuracy": "High - based on actual usage tracking" if water_records > 0 else "Low - no historical data yet",
            "note": f"Calculated from {water_records} water usage records"
        }


class AidenTotalWaterMonthSensor(FellowAidenBaseEntity, SensorEntity):
    """Water used this month, from historical tracking data."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "total_water_this_month"
        self._attr_unique_id = f"{entry.entry_id}-total_water_month"
        self._attr_icon = "mdi:water"
        self._attr_native_unit_of_measurement = "L"

    @property
    def native_value(self) -> float | None:
        """Return total water used this month using historical data."""
        # IMPORTANT: Only use historical tracking data, never fallback to device totals
        water_usage = self.coordinator.history_manager.get_water_usage_for_period(30)
        _LOGGER.debug(f"Water usage this month from history: {water_usage}L")
        
        # Ensure we never accidentally return device lifetime totals
        if water_usage is None or water_usage < 0:
            _LOGGER.warning("Invalid water usage value from history manager, returning 0.0")
            return 0.0
            
        return water_usage

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        water_records = self.coordinator.history_manager.get_water_usage_count()
        brew_count = self.coordinator.history_manager.get_brew_count_for_period(30)
        return {
            "historical_records": water_records,
            "brews_this_month": brew_count,
            "accuracy": "High - based on actual usage tracking" if water_records > 0 else "Low - no historical data yet",
            "note": f"Calculated from {water_records} water usage records"
        }


class AidenAverageBrewDurationSensor(FellowAidenBaseEntity, SensorEntity):
    """Average brew duration across historical data, with last-brew fallback."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "average_brew_duration"
        self._attr_unique_id = f"{entry.entry_id}-avg_brew_duration"
        self._attr_icon = "mdi:timer"
        self._attr_native_unit_of_measurement = "minutes"

    @property
    def native_value(self) -> float | None:
        """Return the average brew duration using historical data."""
        historical_avg = self.coordinator.history_manager.get_average_brew_duration()
        if historical_avg:
            return historical_avg
            
        # Fallback to last brew duration if no historical data
        device_config = self.coordinator.data.get("device_config", {})
        start_time_str = device_config.get("brewStartTime")
        end_time_str = device_config.get("brewEndTime")

        if not start_time_str or not end_time_str:
            return None

        try:
            start_timestamp = int(start_time_str)
            end_timestamp = int(end_time_str)

            if start_timestamp == 0 or end_timestamp == 0:
                return None
            if start_timestamp < TIMESTAMP_2024_01_01 or end_timestamp < TIMESTAMP_2024_01_01:
                return None

            duration_seconds = end_timestamp - start_timestamp
            if duration_seconds < 0:
                return None

            return round(duration_seconds / 60.0, 1)  # Convert to minutes
        except (ValueError, TypeError) as error:
            _LOGGER.error("Error calculating brew duration: %s", error)
            return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        brew_records = self.coordinator.history_manager.get_brew_history_count()
        historical_avg = self.coordinator.history_manager.get_average_brew_duration()
        return {
            "historical_brews": brew_records,
            "accuracy": "High - based on historical averages" if historical_avg else "Low - using last brew only",
            "note": f"Calculated from {brew_records} recorded brews" if historical_avg else "Fallback to last brew duration"
        }


class AidenMostPopularProfileSensor(FellowAidenBaseEntity, SensorEntity):
    """Most-brewed profile, based on historical usage counts."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "most_popular_profile"
        self._attr_unique_id = f"{entry.entry_id}-most_popular_profile"
        self._attr_icon = "mdi:star"

    @property
    def native_value(self) -> str | None:
        """Return the most popular profile name using historical data."""
        # Try to get most popular from historical data
        most_popular = self.coordinator.history_manager.get_most_popular_profile()
        if most_popular:
            return most_popular
            
        # Fallback to default or first profile
        data = self.coordinator.data
        if not data or "profiles" not in data or not data["profiles"]:
            return "No profiles available"
        
        # Look for default profile first
        default_profile = next(
            (p for p in data["profiles"] if p.get("isDefaultProfile")), 
            None
        )
        if default_profile:
            return default_profile.get("title", "Default Profile")
        
        # Otherwise return the first profile
        return data["profiles"][0].get("title", "Profile 1")

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        data = self.coordinator.data
        total_profiles = len(data.get("profiles", [])) if data else 0
        profile_stats = self.coordinator.history_manager.get_profile_usage_stats()
        most_popular = self.coordinator.history_manager.get_most_popular_profile()
        
        attrs = {
            "total_profiles": total_profiles,
            "profile_usage_stats": profile_stats,
        }
        
        if most_popular and profile_stats:
            attrs["accuracy"] = "High - based on actual usage tracking"
            attrs["note"] = f"Based on {sum(profile_stats.values())} recorded brews"
            attrs["usage_count"] = profile_stats.get(most_popular, 0)
        else:
            attrs["accuracy"] = "Low - using default/first profile"
            attrs["note"] = "No historical usage data available yet"
            
        return attrs


class AidenCurrentProfileSensor(FellowAidenBaseEntity, SensorEntity):
    """The currently selected or most recently used brew profile."""

    def __init__(
        self,
        coordinator: FellowAidenDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "current_profile"
        self._attr_unique_id = f"{entry.entry_id}-current_profile"
        self._attr_icon = "mdi:coffee"
        self.detection_method = "unknown"
        self.confidence = "low"

    @property
    def native_value(self) -> str | None:
        """Return the current profile name."""
        _LOGGER.debug("Getting current profile value")
        data = self.coordinator.data
        _LOGGER.debug(f"Data available: {data is not None}, profiles count: {len(data.get('profiles', [])) if data else 0}")

        if data and "profiles" in data and data["profiles"]:
            # Method 1: Check against the "ibSelectedProfileId" field, if set.
            device_config = data.get("device_config")
            if device_config:
                selected_profile_id = device_config.get("ibSelectedProfileId")
                if selected_profile_id:
                    selected_profile = next(
                        (p for p in data["profiles"] if p.get("id") == selected_profile_id),
                        None
                    )
                    if selected_profile:
                        self.detection_method = "Selected Profile Id"
                        self.confidence = "very_high"
                        return selected_profile.get("title", "Selected Profile")

            # Method 2: Check for most recently used profile by lastUsedTime
            profiles_with_last_used = []
            for profile in data["profiles"]:
                last_used = profile.get("lastUsedTime")
                if last_used and last_used != "0":
                    try:
                        last_used_timestamp = int(last_used)
                        if last_used_timestamp > 0:
                            profiles_with_last_used.append((profile, last_used_timestamp))
                    except (ValueError, TypeError):
                        continue

            # Sort by lastUsedTime descending and return the most recent
            if profiles_with_last_used:
                profiles_with_last_used.sort(key=lambda x: x[1], reverse=True)
                most_recent_profile = profiles_with_last_used[0][0]
                _LOGGER.debug(f"Found most recent profile: {most_recent_profile.get('title')} (lastUsedTime: {profiles_with_last_used[0][1]})")
                self.detection_method = "Recent Profile"
                self.confidence = "very_high"
                return most_recent_profile.get("title", "Recent Profile")

        # Method 3: Check for default profile flag
        if data and "profiles" in data and data["profiles"]:
            default_profile = next(
                (p for p in data["profiles"] if p.get("isDefaultProfile")),
                None
            )
            if default_profile:
                _LOGGER.debug(f"Using default profile: {default_profile.get('title')}")
                self.detection_method = "Default Profile"
                self.confidence = "medium"
                return default_profile.get("title", "Default Profile")

        # Method 4: Use most popular profile from history
        most_popular = self.coordinator.history_manager.get_most_popular_profile()
        if most_popular:
            _LOGGER.debug(f"Using most popular from history: {most_popular}")
            self.detection_method = "historical_usage"
            self.confidence = "low_medium"
            return most_popular

        # Method 5: Fallback to first available profile
        if data and "profiles" in data and data["profiles"]:
            _LOGGER.debug("Using first available profile")
            self.detection_method = "first_available"
            self.confidence = "low"
            return data["profiles"][0].get("title", "Profile 1")

        return "No profiles available"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        data = self.coordinator.data
        total_profiles = len(data.get("profiles", [])) if data else 0

        last_used_time = None

        if data and "profiles" in data and data["profiles"]:
            # Get last used time for display
            profiles_with_last_used = []
            for profile in data["profiles"]:
                last_used = profile.get("lastUsedTime")
                if last_used and last_used != "0":
                    try:
                        last_used_timestamp = int(last_used)
                        if last_used_timestamp > 0:
                            profiles_with_last_used.append((profile, last_used_timestamp))
                    except (ValueError, TypeError):
                        continue

            if profiles_with_last_used:
                from homeassistant.util import dt as dt_util
                profiles_with_last_used.sort(key=lambda x: x[1], reverse=True)
                most_recent_timestamp = profiles_with_last_used[0][1]
                try:
                    last_used_dt = dt_util.as_local(dt_util.utc_from_timestamp(most_recent_timestamp))
                    last_used_time = last_used_dt.isoformat()
                except (ValueError, OSError, OverflowError):
                    pass

        attrs = {
            "total_profiles": total_profiles,
            "detection_method": self.detection_method,
            "confidence": self.confidence,
        }
        
        # Add last used time if available
        if last_used_time:
            attrs["last_used_time"] = last_used_time
        
        # Add last brew information if available
        last_brew_time = self.coordinator.history_manager.get_last_brew_time()
        if last_brew_time:
            attrs["last_brew_time"] = last_brew_time.isoformat()
        
        # Add profile usage stats
        profile_stats = self.coordinator.history_manager.get_profile_usage_stats()
        if profile_stats:
            attrs["profile_usage_stats"] = profile_stats
            attrs["total_historical_brews"] = sum(profile_stats.values())
        
        return attrs


class AidenBasketSensor(FellowAidenBaseEntity, SensorEntity):
    """Which basket is inserted: single serve, batch brew, or missing."""

    def __init__(self, coordinator: FellowAidenDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._attr_translation_key = "basket"
        self._attr_unique_id = f"{entry.entry_id}-basket"
        self._attr_icon = "mdi:basket"

    @property
    def native_value(self) -> str:
        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})
        single_basket = device_config.get("singleBrewBasketPresent", False)
        batch_basket = device_config.get("batchBrewBasketPresent", False)

        if single_basket:
            return "Single Serve"
        if batch_basket:
            return "Batch Brew"
        return "Missing"
