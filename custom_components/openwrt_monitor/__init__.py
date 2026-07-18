"""OpenWrt Device Monitor integration for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenWrtMonitorApi
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONF_URL,
    CONF_IDENTITY_MODE,
    DEFAULT_IDENTITY_MODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .coordinator import OpenWrtMonitorCoordinator

PLATFORMS: list[Platform] = [
    Platform.DEVICE_TRACKER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]


@dataclass(slots=True)
class OpenWrtMonitorRuntimeData:
    """Runtime data stored on the config entry."""

    api: OpenWrtMonitorApi
    coordinator: OpenWrtMonitorCoordinator


if TYPE_CHECKING:
    OpenWrtMonitorConfigEntry = ConfigEntry[OpenWrtMonitorRuntimeData]
else:
    OpenWrtMonitorConfigEntry = ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OpenWrtMonitorConfigEntry,
) -> bool:
    """Set up OpenWrt Device Monitor from a config entry."""
    session = async_get_clientsession(hass)
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    timeout = entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
    identity_mode = entry.data.get(CONF_IDENTITY_MODE, DEFAULT_IDENTITY_MODE)

    api = OpenWrtMonitorApi(
        session=session,
        url=entry.data[CONF_URL],
        token=entry.data[CONF_TOKEN],
        timeout=timeout,
        identity_mode=identity_mode,
    )
    coordinator = OpenWrtMonitorCoordinator(hass, api, scan_interval)

    entry.runtime_data = OpenWrtMonitorRuntimeData(api=api, coordinator=coordinator)

    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: OpenWrtMonitorConfigEntry,
) -> bool:
    """Unload the integration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_options(
    hass: HomeAssistant,
    entry: OpenWrtMonitorConfigEntry,
) -> None:
    """Reload the entry when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)
