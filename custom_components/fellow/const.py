"""Constants for Fellow Aiden."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import FellowAidenDataUpdateCoordinator

type FellowAidenConfigEntry = ConfigEntry[FellowAidenDataUpdateCoordinator]

DOMAIN = "fellow"
PLATFORMS = ["sensor", "select", "binary_sensor"]

# Update intervals
DEFAULT_UPDATE_INTERVAL_MINUTES = 1
MIN_UPDATE_INTERVAL_SECONDS = 30


# Historical data constants
HISTORY_RETENTION_DAYS = 365
TIMESTAMP_2024_01_01 = 1704067201  # Used for timestamp validation
MIN_VALID_YEAR = 2023

# Water amount limits (from Fellow API)
MIN_WATER_AMOUNT_ML = 150
MAX_WATER_AMOUNT_ML = 1500

# Data validation thresholds
MIN_HISTORICAL_DATA_FOR_ACCURACY = 2

# Profile defaults
DEFAULT_PROFILE_TYPE = 0
