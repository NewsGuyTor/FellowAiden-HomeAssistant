# Fellow Aiden Integration for Home Assistant

> *“A good brew is like a good friend: reliable, comforting, and occasionally in need of a little maintenance.”*  

Welcome to **Fellow Aiden**, a custom integration that brings your coffee brewer into the Home Assistant universe. Because life’s too short for bad coffee and disconnected devices.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities & Services](#entities--services)
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Brew Profiles:** Create, list, and delete brew profiles from Home Assistant. No more rummaging for the perfect ratio at dawn.
- **Real-Time Sensors:**
  - **Binary sensors** for lid status, missing water, baskets inserted, etc.  
  - **Sensors** for chime volume, brew cycles, and more—because data is beautiful.
- **Device Info:** Displays firmware version, hardware elevation (for you mountaintop dwellers), Wi-Fi and Bluetooth addresses, plus a witty sense of connectedness.

Don’t worry; we left the comedic potential of coffee puns mostly untapped—**mostly**.

---

## Installation

1. **Get the Files**  
   - Download or clone this repository into your Home Assistant’s `config/custom_components/fellow_aiden` folder.  
     ```bash
     cd /config/custom_components
     git clone https://github.com/yourusername/fellow_aiden.git
     # or manually place the files into fellow_aiden/
     ```
   - Ensure the folder is named exactly `fellow_aiden`.

2. **Restart Home Assistant**  
   - This will allow Home Assistant to discover the new integration.

3. **Add Integration**  
   - In Home Assistant’s **Settings > Devices & Services**, click **Add Integration**.  
   - Find “Fellow Aiden,” select it, then follow the prompts to log in with your brewer account credentials.

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

## Entities & Services

### Binary Sensors
- **Lid**: Tells you whether the lid is open or closed (in Home Assistant terms, “on” = open, “off” = closed).  
- **Carafe Inserted**: Quick check for whether the carafe is in place.  
- **Missing Water**: Warns you if you forgot to add water. (We’ve all been there. No judgment.)  

### Sensors
- **Chime Volume**: Current beep level.  
- **Total Brewing Cycles**: For bragging rights or diagnosing coffee obsession.  
- **Water Quantity**: Keep an eye on how many milliliters remain.  

### Services
- **`fellow_aiden.create_profile`**: Takes a JSON with brew settings (ratio, bloom, pulses, etc.) and creates a new profile in the brewer.  
- **`fellow_aiden.delete_profile`**: Remove that ill-fated experimental profile from existence.

---

## FAQ & Troubleshooting

1. **It says “Device not found.”**  
   - Make sure you actually have a Fellow Aiden brewer configured with the same account. That helps.  
2. **I see “unknown” for some sensors.**  
   - Possibly the brewer hasn’t updated yet or the sensor values are missing from the device’s API. Wait a minute or two (literally).  
3. **My baskets are showing up as On/Off—why not “Home”/”Away?”**  
   - Because baskets aren’t known for packing suitcases, we changed the device class to `None`. They’re either inserted (On) or not (Off).

---

## Contributing

- **Issues**: Spot a bug, have a feature request, or can’t resist a coffee pun? [Open an issue](https://github.com/yourusername/fellow_aiden/issues).  
- **PRs**: Fork, code, and send a pull request. We welcome improvements—just keep code style and good taste in brew puns consistent.  
- **Local Testing**: If you break something, revert changes or blame the brew cycle. Either is acceptable.

---

## License

This project is released under the [MIT License](LICENSE). Use it, change it, share it—just don’t blame us if your coffee cravings skyrocket.

---

**Enjoy** your now-connected coffee brewer, and may your mornings be bright, your lid properly closed, and your ratio always 16:1. ☕  