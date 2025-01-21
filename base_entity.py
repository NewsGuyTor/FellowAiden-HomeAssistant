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

        # Extract necessary device information
        brewer_id = device_config.get("id") or self._entry_id
        fw_version = device_config.get("firmwareVersion")
        wifi_mac = device_config.get("wifiMacAddress")
        bt_mac = device_config.get("btMacAddress")
        # local_ip = device_config.get("localIpAddress")  # If you want a config URL, see below

        return {
            "identifiers": {(DOMAIN, brewer_id)},
            "name": data.get("brewer_name", "Fellow Aiden Brewer"),
            "manufacturer": "Fellow",
            "model": "Aiden",
            "sw_version": fw_version,
            "connections": {
                (dr.CONNECTION_NETWORK_MAC, wifi_mac),
                (dr.CONNECTION_BLUETOOTH, bt_mac),
            },
            # If you want to display local IP in the device page, you can do:
            # "configuration_url": f"http://{local_ip}" if local_ip else None,
        }

    @property
    def extra_state_attributes(self):
        """
        Return extra attributes for this entity, e.g. WiFi SSID, local IP, etc.
        These appear in Developer Tools > States.
        """
        data = self.coordinator.data
        device_config = data.get("device_config", {})
        attrs = {}

        # Add WiFi SSID if available
        wifi_ssid = device_config.get("wifiSSID")
        if wifi_ssid:
            attrs["wifi_ssid"] = wifi_ssid

        # If you want to show local IP as an attribute:
        local_ip = device_config.get("localIpAddress")
        if local_ip:
            attrs["local_ip_address"] = local_ip

        return attrs
