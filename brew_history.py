"""Brew history data management for Fellow Aiden integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers import storage

from .const import HISTORY_RETENTION_DAYS, MIN_HISTORICAL_DATA_FOR_ACCURACY

_LOGGER = logging.getLogger(__name__)


class BrewHistoryManager:
    """Manages historical brew data storage and calculations using async file operations."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the brew history manager."""
        self.hass = hass
        self.entry_id = entry_id
        self._store = storage.Store(hass, 1, f"fellow_aiden_history_{entry_id}")
        self._brew_history: list[dict[str, Any]] = []
        self._water_usage_history: list[dict[str, Any]] = []
        self._profile_usage: dict[str, int] = {}
        self._last_total_brews = 0
        self._last_total_water = 0
        self._data_loaded = False

    async def async_load_history(self) -> None:
        """Load historical data from storage."""
        try:
            data = await self._store.async_load()
            if data is not None:
                self._brew_history = data.get("brew_history", [])
                self._water_usage_history = data.get("water_usage_history", [])
                self._profile_usage = data.get("profile_usage", {})
                self._last_total_brews = data.get("last_total_brews", 0)
                self._last_total_water = data.get("last_total_water", 0)
                _LOGGER.debug("Loaded brew history: %d brews, %d water records", 
                            len(self._brew_history), len(self._water_usage_history))
            self._data_loaded = True
        except Exception as e:
            _LOGGER.error("Failed to load brew history: %s", e)
            self._brew_history = []
            self._water_usage_history = []
            self._profile_usage = {}
            self._data_loaded = True

    async def _async_save_history(self) -> None:
        """Save historical data to storage."""
        if not self._data_loaded:
            return
            
        try:
            data = {
                "brew_history": self._brew_history,
                "water_usage_history": self._water_usage_history,
                "profile_usage": self._profile_usage,
                "last_total_brews": self._last_total_brews,
                "last_total_water": self._last_total_water,
                "last_updated": datetime.now().isoformat()
            }
            await self._store.async_save(data)
            _LOGGER.debug("Saved brew history")
        except Exception as e:
            _LOGGER.error("Failed to save brew history: %s", e)

    async def async_update_data(self, device_config: dict[str, Any], profiles: list[dict[str, Any]]) -> None:
        """Update historical data with new device information."""
        # Ensure data is loaded first
        if not self._data_loaded:
            await self.async_load_history()
            
        current_total_brews = device_config.get("totalBrewingCycles", 0)
        current_total_water = device_config.get("totalWaterVolumeL", 0)
        brew_start_time = device_config.get("brewStartTime")
        brew_end_time = device_config.get("brewEndTime")
        
        now = datetime.now()
        data_changed = False
        
        # Initialize baselines if this is the first time we're tracking
        # and we don't have any historical data
        if (self._last_total_brews == 0 and self._last_total_water == 0 and 
            len(self._brew_history) == 0 and len(self._water_usage_history) == 0):
            _LOGGER.info("Initializing water usage tracking baseline: %d brews, %d ml water", 
                        current_total_brews, current_total_water)
            self._last_total_brews = current_total_brews
            self._last_total_water = current_total_water
            data_changed = True
        
        # Check if we have a new brew
        if current_total_brews > self._last_total_brews:
            new_brews = current_total_brews - self._last_total_brews
            _LOGGER.info("Detected %d new brew(s)", new_brews)
            
            # Add brew record(s)
            for i in range(new_brews):
                brew_record = {
                    "timestamp": now.isoformat(),
                    "total_brews_at_time": current_total_brews - (new_brews - 1 - i),
                    "total_water_at_time": current_total_water,
                }
                
                # Add timing information if available
                if brew_start_time and brew_end_time:
                    try:
                        start_ts = int(brew_start_time)
                        end_ts = int(brew_end_time)
                        if start_ts > 0 and end_ts > 0 and start_ts < end_ts:
                            brew_record["start_time"] = datetime.fromtimestamp(start_ts).isoformat()
                            brew_record["end_time"] = datetime.fromtimestamp(end_ts).isoformat()
                            brew_record["duration_seconds"] = end_ts - start_ts
                    except (ValueError, TypeError):
                        pass
                
                # Try to determine the profile used (get default or first profile)
                if profiles:
                    default_profile = next(
                        (p for p in profiles if p.get("isDefaultProfile")), 
                        profiles[0] if profiles else None
                    )
                    if default_profile:
                        profile_id = default_profile.get("id")
                        profile_title = default_profile.get("title", "Unknown Profile")
                        brew_record["profile_id"] = profile_id
                        brew_record["profile_title"] = profile_title
                        
                        # Update profile usage counter
                        if profile_title in self._profile_usage:
                            self._profile_usage[profile_title] += 1
                        else:
                            self._profile_usage[profile_title] = 1
                
                self._brew_history.append(brew_record)
            
            self._last_total_brews = current_total_brews
            data_changed = True
        
        # Check if water usage changed
        if current_total_water > self._last_total_water:
            water_used = current_total_water - self._last_total_water
            water_record = {
                "timestamp": now.isoformat(),
                "water_used_ml": water_used,
                "total_water_at_time": current_total_water,
            }
            self._water_usage_history.append(water_record)
            self._last_total_water = current_total_water
            _LOGGER.debug("Recorded water usage: %d ml", water_used)
            data_changed = True
        
        if data_changed:
            # Clean old records based on retention policy
            cutoff_date = now - timedelta(days=HISTORY_RETENTION_DAYS)
            self._clean_old_records(cutoff_date)
            
            # Save updated history
            await self._async_save_history()

    def _clean_old_records(self, cutoff_date: datetime) -> None:
        """Remove records older than cutoff date."""
        cutoff_iso = cutoff_date.isoformat()
        
        original_brew_count = len(self._brew_history)
        original_water_count = len(self._water_usage_history)
        
        self._brew_history = [
            record for record in self._brew_history 
            if record.get("timestamp", "") > cutoff_iso
        ]
        
        self._water_usage_history = [
            record for record in self._water_usage_history 
            if record.get("timestamp", "") > cutoff_iso
        ]
        
        if len(self._brew_history) < original_brew_count or len(self._water_usage_history) < original_water_count:
            _LOGGER.debug("Cleaned old records: %d->%d brews, %d->%d water", 
                         original_brew_count, len(self._brew_history),
                         original_water_count, len(self._water_usage_history))

    def get_average_time_between_brews(self) -> float | None:
        """Calculate average time between brews in hours."""
        if len(self._brew_history) < MIN_HISTORICAL_DATA_FOR_ACCURACY:
            return None
        
        # Get timestamps of brews
        timestamps = []
        for record in self._brew_history:
            try:
                ts = datetime.fromisoformat(record["timestamp"])
                timestamps.append(ts)
            except (ValueError, KeyError):
                continue
        
        if len(timestamps) < MIN_HISTORICAL_DATA_FOR_ACCURACY:
            return None
        
        # Sort timestamps
        timestamps.sort()
        
        # Calculate intervals
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # Convert to hours
            if interval > 0:  # Ignore negative or zero intervals
                intervals.append(interval)
        
        if intervals:
            return round(sum(intervals) / len(intervals), 1)
        
        return None

    def get_water_usage_for_period(self, days: int) -> float:
        """Get total water usage for the specified number of days."""
        if not self._water_usage_history:
            _LOGGER.debug(f"No water usage history available for {days}-day period")
            return 0.0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        total_water = 0.0
        matching_records = 0
        for record in self._water_usage_history:
            if record.get("timestamp", "") > cutoff_iso:
                water_used = record.get("water_used_ml", 0)
                total_water += water_used
                matching_records += 1
                _LOGGER.debug(f"Found water usage record: {water_used}ml on {record.get('timestamp')}")
        
        total_liters = round(total_water / 1000.0, 2)
        _LOGGER.debug(f"Water usage for {days}-day period: {matching_records} records, {total_water}ml ({total_liters}L)")
        return total_liters

    def get_average_brew_duration(self) -> float | None:
        """Calculate average brew duration in minutes."""
        durations = []
        
        for record in self._brew_history:
            duration = record.get("duration_seconds")
            if duration and duration > 0:
                durations.append(duration / 60.0)  # Convert to minutes
        
        if durations:
            return round(sum(durations) / len(durations), 1)
        
        return None

    def get_most_popular_profile(self) -> str | None:
        """Get the most frequently used profile."""
        if not self._profile_usage:
            return None
        
        # Find profile with highest usage count
        most_used = max(self._profile_usage.items(), key=lambda x: x[1])
        return most_used[0]

    def get_profile_usage_stats(self) -> dict[str, int]:
        """Get profile usage statistics."""
        return self._profile_usage.copy()
        
    def get_brew_count_for_period(self, days: int) -> int:
        """Get number of brews in the specified period."""
        if not self._brew_history:
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        count = 0
        for record in self._brew_history:
            if record.get("timestamp", "") > cutoff_iso:
                count += 1
        
        return count

    def get_last_brew_time(self) -> datetime | None:
        """Get the timestamp of the last brew."""
        if not self._brew_history:
            return None
        
        # Get the most recent brew
        latest_record = max(self._brew_history, key=lambda x: x.get("timestamp", ""))
        
        try:
            dt = datetime.fromisoformat(latest_record["timestamp"])
            # Ensure timezone is set
            if dt.tzinfo is None:
                return dt_util.as_local(dt)
            return dt
        except (ValueError, KeyError):
            return None
    
    def debug_water_usage_history(self) -> None:
        """Debug method to log all water usage history."""
        _LOGGER.info(f"Water usage history ({len(self._water_usage_history)} records):")
        for i, record in enumerate(self._water_usage_history):
            timestamp = record.get("timestamp", "Unknown")
            water_used = record.get("water_used_ml", 0)
            total_at_time = record.get("total_water_at_time", 0)
            _LOGGER.info(f"  {i+1}. {timestamp}: +{water_used}ml (total: {total_at_time}ml)")
        
        if not self._water_usage_history:
            _LOGGER.info("  No water usage records found")
            _LOGGER.info(f"  Current tracking state: last_total_water={self._last_total_water}")
    
    async def async_reset_water_tracking(self, current_total_water: int) -> None:
        """Reset water usage tracking with a new baseline."""
        _LOGGER.info("Resetting water usage tracking baseline to %d ml", current_total_water)
        self._water_usage_history.clear()
        self._last_total_water = current_total_water
        await self._async_save_history()
        _LOGGER.info("Water usage tracking reset complete")