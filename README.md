# HASS OpenWrt Monitor

[![Validate](https://github.com/arkylin/HASS-OpenWrt-Monitor/actions/workflows/validate.yml/badge.svg)](https://github.com/arkylin/HASS-OpenWrt-Monitor/actions/workflows/validate.yml)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=arkylin&repository=HASS-OpenWrt-Monitor&category=integration)

Home Assistant custom integration for a local OpenWrt-style `/devices` API.

It polls an endpoint like:

```bash
curl --location 'http://<your-router-ip>:8082/devices' \
  --header 'Authorization: Bearer <your-token>'
```

and creates Home Assistant entities from a response shaped like:

```json
{
  "timestamp": 1784349684,
  "count": 7,
  "clients": [
    {
      "mac": "10:ff:e0:e4:4a:2e",
      "ip": "192.168.33.219",
      "hostname": "pve",
      "connected": true,
      "type": "wired",
      "lease_time": 1784389562
    }
  ]
}
```

## What it creates

- `binary_sensor` connectivity entity for every configured device identity.
- Per-device sensors:
  - MAC address
  - IP address
  - Connection type
  - RSSI
  - TX rate
  - RX rate
  - Interface
  - Lease time
- Aggregate sensors:
  - connected clients
  - total clients
  - offline clients
  - API timestamp

The integration does not create `device_tracker` entities. It monitors the raw
client state from the API instead of translating router clients into
`home`/`not_home` presence states.

## Install with HACS

This repository is ready to be installed as a HACS custom repository.

The button above opens Home Assistant directly on the HACS custom repository
flow for `arkylin/HASS-OpenWrt-Monitor`.

Manual HACS path:

1. Open **HACS -> Integrations**.
2. Open the menu in the top-right corner.
3. Choose **Custom repositories**.
4. Add your GitHub repository URL.
5. Select category **Integration**.
6. Install **OpenWrt Device Monitor**.
7. Restart Home Assistant.

## Install manually

1. Copy the folder below into your Home Assistant config directory:

   ```text
   custom_components/openwrt_monitor
   ```

2. Restart Home Assistant.
3. Go to **Settings -> Devices & services -> Add integration**.
4. Search for **OpenWrt Device Monitor**.
5. Enter:
   - API URL: `http://<your-router-ip>:8082/devices`
   - Token: either `<your-token>` or `Bearer <your-token>`
   - Scan interval: default `30` seconds
   - Device identity mode: default `Hostname first, then MAC`

If you enter only `http://host:port`, the integration automatically polls
`http://host:port/devices`.

## Device identity and random MAC addresses

Phones often enable private/random MAC addresses. If Home Assistant uses only
MAC addresses, one physical phone may become many duplicate devices over time.

This integration therefore defaults to:

```text
Hostname first, then MAC
```

That means:

- if a client has a useful hostname, such as `Xiaomi-14`, the entity identity is
  based on that hostname;
- if the hostname is missing or `*`, the entity falls back to the MAC address;
- if the same hostname appears with multiple MAC addresses, the integration
  keeps one Home Assistant device, prefers the connected row, and exposes all
  seen MAC addresses in the `known_macs` attribute.

If you have two different devices with the same hostname, either rename one of
them in DHCP/OpenWrt or choose the `MAC address only` identity mode during setup.

## API requirements

The endpoint must return JSON with:

- `clients`: list of client objects
- each client should include at least `mac` and `connected`

Recommended client fields:

```json
{
  "mac": "28:16:a8:47:4e:50",
  "ip": "192.168.33.193",
  "hostname": "DESKTOP-P32VUM5",
  "rssi": -55,
  "tx_rate": "866.0",
  "rx_rate": "866.0",
  "connected": true,
  "type": "wireless",
  "interface": "rax0",
  "lease_time": 1784383521
}
```

## Security note

This integration is designed for a trusted LAN endpoint. If the API is exposed
outside your local network, use HTTPS or a VPN because the Bearer token is sent
with every poll.

## License

MIT
