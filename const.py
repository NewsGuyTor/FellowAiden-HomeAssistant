"""Constants for Fellow Aiden."""
DOMAIN = "fellow"
PLATFORMS = ["sensor", "select", "binary_sensor"]

# Update intervals
DEFAULT_UPDATE_INTERVAL_MINUTES = 1

# Brew timing constants
DEFAULT_WATER_AMOUNT_ML = 420
BREW_START_DELAY_MINUTES = 2

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
