"""Base entity for Fellow Aiden."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

class FellowAidenBaseEntity(CoordinatorEntity):
    """Base class for all Fellow Aiden entities, attaching them to one device."""

    @property
    def device_info(self) -> dict:
        """Return device info for the brewer device registry."""
        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})

        brewer_id = device_config.get("id") or getattr(self, "_entry_id", None)
        fw_version = device_config.get("firmwareVersion")
        wifi_mac = device_config.get("wifiMacAddress")
        bt_mac = device_config.get("btMacAddress")
        wifi_ssid = device_config.get("wifiSSID")

        # We store "elevation" in hw_version to preserve an interesting detail
        elevation = device_config.get("elevation")  # originally a sensor
        hw_version = f"{elevation}m elevation" if elevation is not None else None

        connections = set()
        if wifi_mac:
            connections.add((dr.CONNECTION_NETWORK_MAC, wifi_mac))
        if bt_mac:
            connections.add((dr.CONNECTION_BLUETOOTH, bt_mac))
        # Add WiFi SSID to device info (custom usage, but it meets your request)
        if wifi_ssid:
            connections.add(("wifi_ssid", wifi_ssid))

        return {
            "identifiers": {(DOMAIN, brewer_id)},
            "name": data.get("brewer_name", "Fellow Aiden Brewer"),
            "manufacturer": "Fellow",
            "model": "Aiden",
            "sw_version": fw_version,
            "hw_version": hw_version,
            "connections": connections,
        }

    @property
    def extra_state_attributes(self) -> dict:
        """
        Return extra attributes for this entity, for any
        additional info that doesn't fit in device_info.
        """
        data = self.coordinator.data or {}
        device_config = data.get("device_config", {})
        attrs: dict[str, str] = {}

        # Expose local IP if available
        if "localIpAddress" in device_config:
            attrs["local_ip_address"] = device_config["localIpAddress"]

        return attrs
