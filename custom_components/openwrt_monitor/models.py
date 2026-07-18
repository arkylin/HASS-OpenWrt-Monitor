"""Data models for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OpenWrtClient:
    """A client returned by the OpenWrt monitor API."""

    identity: str
    mac: str
    known_macs: tuple[str, ...]
    ip: str | None
    hostname: str | None
    connected: bool
    type: str | None
    lease_time: int | None
    rssi: int | None
    tx_rate: str | None
    rx_rate: str | None
    interface: str | None

    @property
    def display_name(self) -> str:
        """Return a friendly display name for the client."""
        if self.hostname and self.hostname != "*":
            return self.hostname
        if self.ip:
            return self.ip
        return self.mac

    @property
    def extra_attributes(self) -> dict[str, Any]:
        """Return useful Home Assistant state attributes."""
        attrs: dict[str, Any] = {
            "identity": self.identity,
            "mac": self.mac,
            "connected": self.connected,
        }
        if len(self.known_macs) > 1:
            attrs["known_macs"] = list(self.known_macs)

        if self.ip:
            attrs["ip"] = self.ip
        if self.hostname:
            attrs["hostname"] = self.hostname
        if self.type:
            attrs["connection_type"] = self.type
        if self.lease_time is not None:
            attrs["lease_time"] = self.lease_time
        if self.rssi is not None:
            attrs["rssi"] = self.rssi
        if self.tx_rate is not None:
            attrs["tx_rate"] = self.tx_rate
        if self.rx_rate is not None:
            attrs["rx_rate"] = self.rx_rate
        if self.interface is not None:
            attrs["interface"] = self.interface

        return attrs


@dataclass(frozen=True, slots=True)
class OpenWrtMonitorData:
    """A normalized API response."""

    timestamp: int | None
    count: int
    clients: dict[str, OpenWrtClient]

    @property
    def connected_count(self) -> int:
        """Return the number of connected clients."""
        return sum(1 for client in self.clients.values() if client.connected)

    @property
    def offline_count(self) -> int:
        """Return the number of offline clients in the response."""
        return sum(1 for client in self.clients.values() if not client.connected)
