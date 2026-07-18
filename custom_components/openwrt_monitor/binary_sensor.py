"""Binary sensor entities for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OpenWrtMonitorConfigEntry
from .entity import OpenWrtMonitorEntity


async def async_setup_entry(
    hass,
    entry: OpenWrtMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-client connectivity binary sensors."""
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
            entities.append(OpenWrtClientConnectedBinarySensor(entry, identity))
        if entities:
            async_add_entities(entities)

    async_add_missing_entities()
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_missing_entities)
    )


class OpenWrtClientConnectedBinarySensor(OpenWrtMonitorEntity, BinarySensorEntity):
    """Represent a client's connected state as a binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, entry: OpenWrtMonitorConfigEntry, identity: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(entry.runtime_data.coordinator, entry.entry_id, identity)
        self._attr_unique_id = f"{entry.entry_id}_{identity}_connected"
        self._attr_name = "Connected"

    @property
    def is_on(self) -> bool:
        """Return true when the client is connected."""
        return bool((client := self.client) and client.connected)
