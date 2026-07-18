"""Config flow for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    OpenWrtMonitorApi,
    OpenWrtMonitorAuthError,
    OpenWrtMonitorConnectionError,
    OpenWrtMonitorInvalidResponseError,
    normalize_url,
)
from .const import (
    CONF_IDENTITY_MODE,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONF_URL,
    DEFAULT_IDENTITY_MODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    IDENTITY_HOSTNAME_OR_MAC,
    IDENTITY_MAC,
)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the user-step form schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_URL, default=defaults.get(CONF_URL, "")): str,
            vol.Required(CONF_TOKEN, default=defaults.get(CONF_TOKEN, "")): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
            vol.Optional(
                CONF_TIMEOUT,
                default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            ): vol.All(vol.Coerce(int), vol.Range(min=3, max=60)),
            vol.Optional(
                CONF_IDENTITY_MODE,
                default=defaults.get(CONF_IDENTITY_MODE, DEFAULT_IDENTITY_MODE),
            ): vol.In([IDENTITY_HOSTNAME_OR_MAC, IDENTITY_MAC]),
        }
    )


def _options_schema(scan_interval: int) -> vol.Schema:
    """Return the options form schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=scan_interval,
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
        }
    )


async def _validate_input(
    hass: HomeAssistant,
    user_input: dict[str, Any],
) -> tuple[str, str]:
    """Validate user input and return normalized URL plus title."""
    normalized_url = normalize_url(user_input[CONF_URL])
    session = async_get_clientsession(hass)
    api = OpenWrtMonitorApi(
        session=session,
        url=normalized_url,
        token=user_input[CONF_TOKEN],
        timeout=user_input[CONF_TIMEOUT],
        identity_mode=user_input.get(CONF_IDENTITY_MODE, DEFAULT_IDENTITY_MODE),
    )
    await api.async_get_devices()

    parsed = urlparse(normalized_url)
    title = parsed.netloc or normalized_url
    return normalized_url, title


class OpenWrtMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an OpenWrt Device Monitor config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized_url, title = await _validate_input(self.hass, user_input)
            except OpenWrtMonitorAuthError:
                errors["base"] = "invalid_auth"
            except OpenWrtMonitorConnectionError:
                errors["base"] = "cannot_connect"
            except OpenWrtMonitorInvalidResponseError:
                errors["base"] = "invalid_response"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(normalized_url)
                self._abort_if_unique_id_configured()
                data = dict(user_input)
                data[CONF_URL] = normalized_url
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Handle a reauthentication flow."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Ask the user for a new token."""
        errors: dict[str, str] = {}

        if user_input is not None and self._reauth_entry is not None:
            entry = self._reauth_entry
            data = dict(entry.data)
            data[CONF_TOKEN] = user_input[CONF_TOKEN]
            try:
                await _validate_input(self.hass, data)
            except OpenWrtMonitorAuthError:
                errors["base"] = "invalid_auth"
            except OpenWrtMonitorConnectionError:
                errors["base"] = "cannot_connect"
            except OpenWrtMonitorInvalidResponseError:
                errors["base"] = "invalid_response"
            except Exception:
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OpenWrtMonitorOptionsFlow:
        """Return the options flow."""
        return OpenWrtMonitorOptionsFlow(config_entry)


class OpenWrtMonitorOptionsFlow(config_entries.OptionsFlow):
    """Handle OpenWrt Device Monitor options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(scan_interval),
        )
