"""Data update coordinator for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OpenWrtMonitorApi,
    OpenWrtMonitorAuthError,
    OpenWrtMonitorConnectionError,
    OpenWrtMonitorInvalidResponseError,
)
from .const import DOMAIN
from .models import OpenWrtMonitorData

_LOGGER = logging.getLogger(__name__)


class OpenWrtMonitorCoordinator(DataUpdateCoordinator[OpenWrtMonitorData]):
    """Fetch OpenWrt monitor data on a fixed interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: OpenWrtMonitorApi,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> OpenWrtMonitorData:
        """Fetch fresh data from the API."""
        try:
            return await self.api.async_get_devices()
        except OpenWrtMonitorAuthError as err:
            raise ConfigEntryAuthFailed("OpenWrt monitor token was rejected") from err
        except (
            OpenWrtMonitorConnectionError,
            OpenWrtMonitorInvalidResponseError,
        ) as err:
            raise UpdateFailed(str(err)) from err

