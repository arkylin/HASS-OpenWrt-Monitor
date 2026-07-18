"""Shared entity helpers for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from homeassistant.const import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OpenWrtMonitorCoordinator
from .models import OpenWrtClient


class OpenWrtMonitorEntity(CoordinatorEntity[OpenWrtMonitorCoordinator]):
    """Base entity for monitor-backed entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OpenWrtMonitorCoordinator,
        entry_id: str,
        identity: str,
    ) -> None:
        """Initialize a client entity."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._identity = identity

    @property
    def client(self) -> OpenWrtClient | None:
        """Return the current client data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.clients.get(self._identity)

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device registry information."""
        name = self._identity
        if (client := self.client) is not None:
            name = client.display_name

        info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._identity}")},
            name=name,
            manufacturer="OpenWrt",
        )
        if (client := self.client) is not None:
            info["connections"] = {(CONNECTION_NETWORK_MAC, client.mac)}
        return info

    @property
    def available(self) -> bool:
        """Return whether the client is present in the latest response."""
        return self.client is not None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return shared client attributes."""
        if (client := self.client) is None:
            return None
        return client.extra_attributes
