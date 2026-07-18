"""API client for the OpenWrt Device Monitor integration."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from urllib.parse import urlparse, urlunparse

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import IDENTITY_HOSTNAME_OR_MAC
from .models import OpenWrtClient, OpenWrtMonitorData


class OpenWrtMonitorError(Exception):
    """Base error for OpenWrt monitor API failures."""


class OpenWrtMonitorAuthError(OpenWrtMonitorError):
    """Raised when the API rejects authentication."""


class OpenWrtMonitorConnectionError(OpenWrtMonitorError):
    """Raised when the API cannot be reached."""


class OpenWrtMonitorInvalidResponseError(OpenWrtMonitorError):
    """Raised when the API returns unexpected data."""


def normalize_url(value: str) -> str:
    """Normalize a user-provided API URL.

    Users may paste either the full endpoint or just host:port. The integration
    always stores and polls the concrete /devices endpoint.
    """
    url = value.strip()
    if "://" not in url:
        url = f"http://{url}"

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise OpenWrtMonitorInvalidResponseError("Invalid URL")

    path = parsed.path.rstrip("/")
    if not path:
        path = "/devices"

    normalized = parsed._replace(path=path, params="", query="", fragment="")
    return urlunparse(normalized)


def authorization_header(token: str) -> str:
    """Return a valid Authorization header value from a raw or Bearer token."""
    value = token.strip()
    if value.lower().startswith("bearer "):
        return value
    return f"Bearer {value}"


def _as_optional_str(value: Any) -> str | None:
    """Normalize an optional string-ish value."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_int(value: Any) -> int | None:
    """Normalize an optional integer-ish value."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    """Normalize bool values from strict JSON or string-like responses."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _valid_hostname(hostname: str | None) -> bool:
    """Return true if hostname is useful as a stable identity."""
    return bool(hostname and hostname != "*")


def _identity_key(mac: str, hostname: str | None, identity_mode: str) -> str:
    """Return the stable Home Assistant identity key for a client."""
    if identity_mode == IDENTITY_HOSTNAME_OR_MAC and _valid_hostname(hostname):
        return f"hostname:{hostname.lower()}"
    return f"mac:{mac}"


def _merge_clients(existing: OpenWrtClient, candidate: OpenWrtClient) -> OpenWrtClient:
    """Merge two API rows that represent the same configured identity.

    This mainly handles phones that rotate private MAC addresses while keeping
    a stable hostname. Prefer the connected row, then the newest lease.
    """
    known_macs = tuple(sorted({*existing.known_macs, *candidate.known_macs}))

    existing_rank = (
        1 if existing.connected else 0,
        existing.lease_time or 0,
    )
    candidate_rank = (
        1 if candidate.connected else 0,
        candidate.lease_time or 0,
    )

    winner = candidate if candidate_rank >= existing_rank else existing
    return replace(winner, known_macs=known_macs)


def parse_monitor_data(
    payload: dict[str, Any],
    identity_mode: str = IDENTITY_HOSTNAME_OR_MAC,
) -> OpenWrtMonitorData:
    """Parse and validate the monitor API response."""
    clients_payload = payload.get("clients")
    if not isinstance(clients_payload, list):
        raise OpenWrtMonitorInvalidResponseError("Response does not contain a clients list")

    clients: dict[str, OpenWrtClient] = {}
    for item in clients_payload:
        if not isinstance(item, dict):
            continue

        mac = _as_optional_str(item.get("mac"))
        if not mac:
            continue

        normalized_mac = mac.lower()
        hostname = _as_optional_str(item.get("hostname"))
        identity = _identity_key(normalized_mac, hostname, identity_mode)
        client = OpenWrtClient(
            identity=identity,
            mac=normalized_mac,
            known_macs=(normalized_mac,),
            ip=_as_optional_str(item.get("ip")),
            hostname=hostname,
            connected=_as_bool(item.get("connected")),
            type=_as_optional_str(item.get("type")),
            lease_time=_as_optional_int(item.get("lease_time")),
            rssi=_as_optional_int(item.get("rssi")),
            tx_rate=_as_optional_str(item.get("tx_rate")),
            rx_rate=_as_optional_str(item.get("rx_rate")),
            interface=_as_optional_str(item.get("interface")),
        )
        if identity in clients:
            clients[identity] = _merge_clients(clients[identity], client)
        else:
            clients[identity] = client

    count = _as_optional_int(payload.get("count"))
    return OpenWrtMonitorData(
        timestamp=_as_optional_int(payload.get("timestamp")),
        count=count if count is not None else len(clients),
        clients=clients,
    )


class OpenWrtMonitorApi:
    """Small async client for the devices endpoint."""

    def __init__(
        self,
        session: ClientSession,
        url: str,
        token: str,
        timeout: int,
        identity_mode: str,
    ) -> None:
        """Initialize the API client."""
        self.url = normalize_url(url)
        self._session = session
        self._token = token
        self._timeout = timeout
        self._identity_mode = identity_mode

    async def async_get_devices(self) -> OpenWrtMonitorData:
        """Fetch and normalize devices from the API."""
        try:
            response = await self._session.get(
                self.url,
                headers={"Authorization": authorization_header(self._token)},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = await response.json(content_type=None)
        except ClientResponseError as err:
            if err.status in {401, 403}:
                raise OpenWrtMonitorAuthError("Invalid token") from err
            raise OpenWrtMonitorConnectionError(f"HTTP {err.status}") from err
        except ClientError as err:
            raise OpenWrtMonitorConnectionError(str(err)) from err

        if not isinstance(payload, dict):
            raise OpenWrtMonitorInvalidResponseError("Response is not a JSON object")

        return parse_monitor_data(payload, self._identity_mode)
