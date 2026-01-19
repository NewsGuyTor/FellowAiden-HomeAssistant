# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Fellow Aiden coffee brewers. The integration connects to Fellow's cloud API to provide real-time monitoring, control, and profile management for Fellow Aiden brewing devices.

**Domain**: `fellow`
**Integration Type**: Cloud polling (IoT class)

## Architecture

### Core Components

- **`manifest.json`**: Integration metadata (version, dependencies, domain, IoT class)
- **`__init__.py`**: Main integration entry point, handles setup/teardown and service registration
- **`coordinator.py`**: Data update coordinator that polls Fellow's cloud API every minute
- **`fellow_aiden/`**: Vendored Fellow Aiden Python library for API communication
- **`config_flow.py`**: Configuration flow for user authentication setup
- **`base_entity.py`**: Base entity class that provides device registry info and common attributes

### Platform Files

- **`sensor.py`**: Sensors for water usage, brew counts, timestamps, and calculated metrics
- **`binary_sensor.py`**: Binary sensors for brewing status, lid position, water level, etc.
- **`select.py`**: Select entities for choosing brew profiles

### Key Data Flow

1. **Authentication**: Users provide email/password via config flow
2. **Data Fetching**: Coordinator polls Fellow's API using vendored library
3. **Entity Updates**: Sensors and binary sensors update from coordinator data
4. **Device Registry**: All entities are grouped under a single device per brewer

## Development Notes

### Fellow Aiden Library (Vendored)

The integration includes a vendored copy of the Fellow Aiden library in `fellow_aiden/`:
- **`__init__.py`**: Main `FellowAiden` class with API methods
- **`profile.py`**: Pydantic models for coffee profiles
- **`schedule.py`**: Pydantic models for brewing schedules

**Key Features**:
- **HTTP Retries**: Built-in retry logic for failed requests (3 retries for 4xx/5xx errors)
- **Lazy Loading**: Profiles and schedules are fetched on-demand via `@property` decorators
- **Performance**: Profile validation removed from delete operations for speed

**Important**: The coordinator uses private method hacks (`_FellowAiden__device()`, `_FellowAiden__auth()`) to force data refreshes, as the library doesn't expose public refresh methods.

### Services

Two custom services are registered:
- **`fellow.create_profile`**: Create new brew profiles with detailed parameters
- **`fellow.delete_profile`**: Delete profiles by ID

Service definitions are in `services.yaml` with extensive parameter validation.

### Entity Patterns

- All entities inherit from `FellowAidenBaseEntity` for consistent device info
- Sensors handle various data types (numbers, timestamps, calculated values)
- Binary sensors use appropriate device classes (`RUNNING`, `DOOR`, `PROBLEM`)
- Device info includes MAC addresses, firmware version, and elevation as hardware version

### Authentication & Error Handling

- Initial auth happens during config flow setup
- Coordinator handles 401 responses by triggering re-authentication
- Library automatically retries failed requests after re-auth
- Update failures are logged but don't crash the integration

## Testing & Debugging

- Enable debug logging for domain `fellow` to see API calls and data updates
- The integration polls every minute - check logs for update patterns
- Device config data structure varies, so entities handle missing keys gracefully
- Profile and schedule data is cached and only refreshed after modifications

## Common Patterns

When adding new sensors:
1. Add to appropriate sensor list in `sensor.py` or `binary_sensor.py`
2. Follow existing patterns for data extraction from coordinator
3. Use appropriate units and device classes
4. Handle missing/None values gracefully

When modifying services:
1. Update `services.yaml` for UI validation
2. Modify service handlers in `__init__.py`
3. Ensure proper error handling and data validation
