# base_entity.py
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

class FellowAidenBaseEntity(CoordinatorEntity):
    """Base class for all Fellow Aiden entities, attaching them to one device."""

    @property
    def device_info(self):
        """Return device info for the brewer device registry."""
        data = self.coordinator.data
        device_config = data.get("device_config", {})

        brewer_id = device_config.get("id") or self._entry_id
        fw_version = device_config.get("firmwareVersion")
        wifi_mac = device_config.get("wifiMacAddress")
        bt_mac = device_config.get("btMacAddress")
        # We'll store "Elevation" in hw_version for the device
        elevation = device_config.get("elevation")  # originally a sensor
        hw_version = None
        if elevation is not None:
            # Example: "Elevation: 120 m"
            hw_version = f"Elevation: {elevation} m"

        return {
            "identifiers": {(DOMAIN, brewer_id)},
            "name": data.get("brewer_name", "Fellow Aiden Brewer"),
            "manufacturer": "Fellow",
            "model": "Aiden",
            "sw_version": fw_version,
            # Use hw_version to hold the elevation text
            "hw_version": hw_version,
            "connections": {
                (dr.CONNECTION_NETWORK_MAC, wifi_mac),
                (dr.CONNECTION_BLUETOOTH, bt_mac),
            },
        }

    @property
    def extra_state_attributes(self):
        """
        Return extra attributes for this entity, for any
        additional info that doesn't fit in device_info.
        For example, if you want to store WiFi SSID or local IP here.
        """
        data = self.coordinator.data
        device_config = data.get("device_config", {})
        attrs = {}

        # If you want to expose WiFi SSID or local IP as attributes:
        if "wifiSSID" in device_config:
            attrs["wifi_ssid"] = device_config["wifiSSID"]
        if "localIpAddress" in device_config:
            attrs["local_ip_address"] = device_config["localIpAddress"]

        return attrs
