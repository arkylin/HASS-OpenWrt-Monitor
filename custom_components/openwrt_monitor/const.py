"""Constants for the OpenWrt Device Monitor integration."""

from __future__ import annotations

DOMAIN = "openwrt_monitor"

CONF_URL = "url"
CONF_TOKEN = "token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TIMEOUT = "timeout"
CONF_IDENTITY_MODE = "identity_mode"

IDENTITY_MAC = "mac"
IDENTITY_HOSTNAME_OR_MAC = "hostname_or_mac"

DEFAULT_NAME = "OpenWrt Device Monitor"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 10
DEFAULT_IDENTITY_MODE = IDENTITY_HOSTNAME_OR_MAC

PLATFORMS = ["device_tracker", "binary_sensor", "sensor"]
