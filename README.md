# Fellow Aiden Integration for Home Assistant

<img src="device.png" alt="Device Image" align="right" width="200"/>

> *“A good brew is like a good friend: reliable, comforting, and occasionally in need of a little maintenance.”*  

This is a custom integration that brings your coffee brewer into the Home Assistant universe. Because life’s too short for bad coffee and disconnected devices.

*Special thanks to [Brandon Dixon (9b)](https://github.com/9b) for creating the [fellow-aiden](https://github.com/9b/fellow-aiden) Python library that laid the groundwork for this integration!*

<sub>You might also like my [Brew.link to Aiden](https://greasyfork.org/en/scripts/524547-brew-link-to-aiden) userscript to send Brew.link profiles directly to your Fellow Aiden.</sub>

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Services](#services)
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Real-Time Sensors:**
  - **Sensors** for water usage, number of brews, average water per brew and more—because data is beautiful.
  - **Analytics:** Daily/weekly/monthly water usage tracking, brew patterns, and timing insights.
  - **Binary sensors** for brewing, lid status, missing water, baskets inserted, etc.
- **Device Info:** Displays firmware version, hardware elevation (for you mountaintop dwellers), Wi-Fi and Bluetooth addresses, plus a witty sense of connectedness.
- **Brew Management:** 
  - Create, list, delete, and manage brew profiles from Home Assistant
  - Schedule management
  - Profile selection dropdown (display-only)
- **Services:** A collection of services for all brewing operations
- **Smart Logging:** Detailed API logging for manual operations, quiet polling for regular updates
- **Water Usage Tracking:** Historical tracking with reset capabilities and period-specific sensors

## Screenshot

<p align="center">
<img width="720" alt="Image" src="https://github.com/user-attachments/assets/6cf8a133-dc34-4ae6-a1e7-845c8d150d25" />
</p>

---

## Installation

Choose one of the following methods to install the **Fellow Aiden** integration:

### 1. Install via HACS

**Prerequisites:**
- **Home Assistant** and **HACS (Home Assistant Community Store)** installed. [HACS Installation Guide](https://hacs.xyz/docs/installation/prerequisites)

**Steps:**

1. **Add the Repository to HACS**
   - Open Home Assistant and go to **Settings > Devices & Services**.
   - Click on **HACS** in the sidebar.
   - Navigate to the **Integrations** tab.
   - Click the **three-dot menu** (⋮) and select **"Add Repository"**.
   - Enter the repository URL:

     ```text
     https://github.com/NewsGuyTor/FellowAiden-HomeAssistant/
     ```

   - Choose **"Integration"** as the category and click **"Add"**.

2. **Install the Integration**
   - In HACS, go to the **Integrations** tab.
   - Click the **"+" (Add)** button.
   - Search for **"Fellow Aiden"** and select it.
   - Click **"Install"**.

3. **Configure the Integration**
   - **Restart Home Assistant**.
   - After restarting, navigate to **Settings > Devices & Services**.
   - Click **"Add Integration"**, find **"Fellow Aiden"**, and follow the prompts to log in with your brewer account credentials.

### 2. Manual Installation

**Steps:**

1. **Download or Clone the Repository**
   ```bash
   cd /config/custom_components
   git clone https://github.com/NewsGuyTor/FellowAiden-HomeAssistant.git fellow
   ```
   - Ensure the folder is named exactly `fellow`.

2. **Restart Home Assistant**
   - This allows Home Assistant to detect the new integration.

3. **Add the Integration**
   - Go to **Settings > Devices & Services**.
   - Click **"Add Integration"**, search for **"Fellow Aiden"**, and follow the prompts to log in with your brewer account credentials.

---

## Configuration

1. **Credentials**  
   - Enter your email and password for the Fellow Aiden account.  
   - Home Assistant saves these securely in its config entry.

2. **Polling Interval**  
   - The integration polls your device every 1 minute by default.  
   - If your brewer starts complaining about the daily grind, consider adjusting the interval in the options flow (if implemented).

3. **Optional Services**  
   - You’ll see **Create Brew Profile** and **Delete Brew Profile** services that let you manage your brewer from automations or the Developer Tools.

---

## Services

### Brew Profile Management

- **`fellow.create_profile`**: Create new brew profiles with detailed parameters (ratio, bloom, pulses, etc.)
- **`fellow.delete_profile`**: Delete profiles by ID
- **`fellow.list_profiles`**: List all available profiles with their names and IDs
- **`fellow.get_profile_details`**: Get detailed information about a specific profile

### Schedule Management

- **`fellow.create_schedule`**: Create brewing schedules with day/time configurations
- **`fellow.delete_schedule`**: Delete schedules by ID
- **`fellow.toggle_schedule`**: Enable or disable existing schedules
- **`fellow.list_schedules`**: List all current schedules with full details

### Brewing Operations

- *No direct start brew service (use device controls or schedules).*

### Analytics & Debugging

- **`fellow.reset_water_tracking`**: Reset water usage tracking baseline
- **`fellow.debug_water_usage`**: Show detailed water usage history
- **`fellow.refresh_and_log_data`**: Manually refresh and log complete API response

All services include error handling and detailed logging for troubleshooting.

---

## FAQ & Troubleshooting

1. **It says “Device not found.”**  
   - Make sure you actually have a Fellow Aiden brewer configured with the same account. That helps.  
2. **I see “Unknown” for some sensors.**  
   - Possibly the brewer hasn’t updated yet or the sensor values are missing from the device’s API. Wait a minute or two (literally). Some others may take longer. Make sure to issue a bug report if they've been “Unknown” for days.

---

## Contributing

- **Issues**: Spot a bug, have a feature request, or can’t resist a coffee pun? [Open an issue](https://github.com/NewsGuyTor/FellowAiden-HomeAssistant/issues).  
- **PRs**: Fork, code, and send a pull request. We welcome improvements—just keep code style and good taste in brew puns consistent.  
- **Local Testing**: If you break something, revert changes or blame the brew cycle. Either is acceptable.

---

## License

This project is released under the [GPL-3.0 license](LICENSE). Use it, change it, share it—just don’t blame us if your coffee cravings skyrocket.

---

**Enjoy** your now-connected coffee brewer, and may your mornings be bright, your lid properly closed, and your water tank never empty.
