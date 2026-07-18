"""Sensor entities for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OpenWrtMonitorConfigEntry
from .const import DOMAIN
from .coordinator import OpenWrtMonitorCoordinator


async def async_setup_entry(
    hass,
    entry: OpenWrtMonitorConfigEntry,
    async_add_entities,
) -> None:
    """Set up aggregate monitor sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            OpenWrtAggregateSensor(
                coordinator,
                entry.entry_id,
                "connected_clients",
                "Connected clients",
                lambda data: data.connected_count,
            ),
            OpenWrtAggregateSensor(
                coordinator,
                entry.entry_id,
                "total_clients",
                "Total clients",
                lambda data: data.count,
            ),
            OpenWrtAggregateSensor(
                coordinator,
                entry.entry_id,
                "offline_clients",
                "Offline clients",
                lambda data: data.offline_count,
            ),
            OpenWrtTimestampSensor(coordinator, entry.entry_id),
        ]
    )


class OpenWrtAggregateSensor(CoordinatorEntity[OpenWrtMonitorCoordinator], SensorEntity):
    """Represent an aggregate numeric sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OpenWrtMonitorCoordinator,
        entry_id: str,
        key: str,
        name: str,
        value_fn,
    ) -> None:
        """Initialize the aggregate sensor."""
        super().__init__(coordinator)
        self._value_fn = value_fn
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = "devices"
        self._attr_icon = "mdi:devices"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "OpenWrt Device Monitor",
            "manufacturer": "OpenWrt",
        }

    @property
    def available(self) -> bool:
        """Return whether coordinator data is available."""
        return self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        """Return the current sensor value."""
        if self.coordinator.data is None:
            return None
        return self._value_fn(self.coordinator.data)


class OpenWrtTimestampSensor(CoordinatorEntity[OpenWrtMonitorCoordinator], SensorEntity):
    """Represent the API timestamp as a timestamp sensor."""

    _attr_has_entity_name = True
    _attr_name = "API timestamp"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(
        self,
        coordinator: OpenWrtMonitorCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the timestamp sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_api_timestamp"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "OpenWrt Device Monitor",
            "manufacturer": "OpenWrt",
        }

    @property
    def available(self) -> bool:
        """Return whether timestamp data is available."""
        return self.coordinator.data is not None and self.coordinator.data.timestamp is not None

    @property
    def native_value(self) -> datetime | None:
        """Return the API timestamp as a timezone-aware datetime."""
        if self.coordinator.data is None or self.coordinator.data.timestamp is None:
            return None
        return datetime.fromtimestamp(self.coordinator.data.timestamp, timezone.utc)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return raw timestamp metadata."""
        if self.coordinator.data is None:
            return {}
        return {"raw_timestamp": self.coordinator.data.timestamp}
