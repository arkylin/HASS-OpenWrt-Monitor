"""Device tracker entities for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OpenWrtMonitorConfigEntry
from .entity import OpenWrtMonitorEntity


async def async_setup_entry(
    hass,
    entry: OpenWrtMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up client device tracker entities."""
    coordinator = entry.runtime_data.coordinator
    known_identities: set[str] = set()

    @callback
    def async_add_missing_entities() -> None:
        entities = []
        if coordinator.data is None:
            return
        for identity in coordinator.data.clients:
            if identity in known_identities:
                continue
            known_identities.add(identity)
            entities.append(OpenWrtClientDeviceTracker(entry, identity))
        if entities:
            async_add_entities(entities)

    async_add_missing_entities()
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_missing_entities)
    )


class OpenWrtClientDeviceTracker(OpenWrtMonitorEntity, ScannerEntity):
    """Represent an OpenWrt client as a Home Assistant device tracker."""

    _attr_has_entity_name = False

    def __init__(self, entry: OpenWrtMonitorConfigEntry, identity: str) -> None:
        """Initialize the device tracker."""
        super().__init__(entry.runtime_data.coordinator, entry.entry_id, identity)
        self._attr_unique_id = f"{entry.entry_id}_{identity}_tracker"

    @property
    def name(self) -> str:
        """Return the entity name."""
        if (client := self.client) is not None:
            return client.display_name
        return self._identity

    @property
    def is_connected(self) -> bool:
        """Return true if the client is connected."""
        return bool((client := self.client) and client.connected)

    @property
    def ip_address(self) -> str | None:
        """Return the current IP address."""
        if (client := self.client) is not None:
            return client.ip
        return None

    @property
    def mac_address(self) -> str | None:
        """Return the MAC address."""
        if (client := self.client) is not None:
            return client.mac
        return None

    @property
    def hostname(self) -> str | None:
        """Return the hostname."""
        if (client := self.client) is None:
            return None
        if not client.hostname or client.hostname == "*":
            return None
        return client.hostname
