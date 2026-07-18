"""Sensor entities for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OpenWrtMonitorConfigEntry
from .const import DOMAIN
from .coordinator import OpenWrtMonitorCoordinator
from .entity import OpenWrtMonitorEntity
from .models import OpenWrtClient


@dataclass(frozen=True, slots=True)
class OpenWrtClientSensorDescription:
    """Describe a per-client sensor."""

    key: str
    name: str
    value_fn: Callable[[OpenWrtClient], Any]
    icon: str | None = None
    device_class: SensorDeviceClass | None = None
    native_unit_of_measurement: str | None = None
    always_create: bool = False


def _lease_time(client: OpenWrtClient) -> datetime | None:
    """Return the DHCP lease time as a timestamp."""
    if client.lease_time is None:
        return None
    return datetime.fromtimestamp(client.lease_time, timezone.utc)


def _float_attr(client: OpenWrtClient, attr: str) -> float | None:
    """Return a float from a string-ish client attribute."""
    value = getattr(client, attr)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


CLIENT_SENSOR_DESCRIPTIONS: tuple[OpenWrtClientSensorDescription, ...] = (
    OpenWrtClientSensorDescription(
        key="mac",
        name="MAC address",
        value_fn=lambda client: client.mac,
        icon="mdi:lan",
        always_create=True,
    ),
    OpenWrtClientSensorDescription(
        key="ip",
        name="IP address",
        value_fn=lambda client: client.ip,
        icon="mdi:ip-network",
        always_create=True,
    ),
    OpenWrtClientSensorDescription(
        key="connection_type",
        name="Connection type",
        value_fn=lambda client: client.type,
        icon="mdi:connection",
        always_create=True,
    ),
    OpenWrtClientSensorDescription(
        key="rssi",
        name="RSSI",
        value_fn=lambda client: client.rssi,
        icon="mdi:wifi-strength-2",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
    ),
    OpenWrtClientSensorDescription(
        key="tx_rate",
        name="TX rate",
        value_fn=lambda client: _float_attr(client, "tx_rate"),
        icon="mdi:upload-network",
        native_unit_of_measurement="Mbit/s",
    ),
    OpenWrtClientSensorDescription(
        key="rx_rate",
        name="RX rate",
        value_fn=lambda client: _float_attr(client, "rx_rate"),
        icon="mdi:download-network",
        native_unit_of_measurement="Mbit/s",
    ),
    OpenWrtClientSensorDescription(
        key="interface",
        name="Interface",
        value_fn=lambda client: client.interface,
        icon="mdi:access-point-network",
    ),
    OpenWrtClientSensorDescription(
        key="lease_time",
        name="Lease time",
        value_fn=_lease_time,
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        always_create=True,
    ),
)


async def async_setup_entry(
    hass,
    entry: OpenWrtMonitorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up aggregate and per-client monitor sensors."""
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

    known_client_sensors: set[tuple[str, str]] = set()

    @callback
    def async_add_missing_client_sensors() -> None:
        entities = []
        if coordinator.data is None:
            return
        for identity, client in coordinator.data.clients.items():
            for description in CLIENT_SENSOR_DESCRIPTIONS:
                if not description.always_create and description.value_fn(client) is None:
                    continue
                entity_key = (identity, description.key)
                if entity_key in known_client_sensors:
                    continue
                known_client_sensors.add(entity_key)
                entities.append(OpenWrtClientSensor(entry, identity, description))
        if entities:
            async_add_entities(entities)

    async_add_missing_client_sensors()
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_missing_client_sensors)
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


class OpenWrtClientSensor(OpenWrtMonitorEntity, SensorEntity):
    """Represent one monitored client field as a sensor."""

    def __init__(
        self,
        entry: OpenWrtMonitorConfigEntry,
        identity: str,
        description: OpenWrtClientSensorDescription,
    ) -> None:
        """Initialize the client sensor."""
        super().__init__(entry.runtime_data.coordinator, entry.entry_id, identity)
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{identity}_{description.key}"
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement

    @property
    def available(self) -> bool:
        """Return whether the field is available for this client."""
        if not super().available or self.client is None:
            return False
        return self.native_value is not None

    @property
    def native_value(self) -> Any:
        """Return the current field value."""
        if (client := self.client) is None:
            return None
        return self._description.value_fn(client)
