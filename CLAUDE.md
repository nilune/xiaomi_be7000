# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a configuration repository for the Xiaomi BE7000 router. It contains setup scripts, configuration files, and documentation for deploying services on the router. The router runs OpenWrt-based firmware with Docker support.

## Environment Variables

These variables are used throughout the documentation and scripts:

```bash
export ROUTER_ADDRESS=<your_router_ip>
export ROUTER_USB_DIR=/mnt/usb-ef8d1024  # External USB drive mount point
```

## Deployment Commands

### Copy files to router
```bash
# Copy configuration files
scp -O <local_path> root@${ROUTER_ADDRESS}:<remote_path>

# Copy directories recursively
scp -O -r <local_dir> root@${ROUTER_ADDRESS}:<remote_path>
```

### SSH into router
```bash
ssh root@${ROUTER_ADDRESS}
```

### Run startup script on router
```bash
/data/startup.sh
```

### Service management on router
```bash
service <service_name> start|stop|restart|enable|disable
# Examples:
service adguardhome restart
service v2raya status
```

## Architecture

### Service Structure

Each service follows this pattern:
1. **Binaries and configs stored on USB drive**: `${ROUTER_USB_DIR}/System/<service_name>/`
2. **Startup script**: Copied to `/data/services/<service_name>.sh` on the router
3. **Symlinks**: Created at boot to link router system paths to USB storage
4. **Init.d script**: OpenWrt procd-based service definition

### Main Startup Flow

1. `/etc/config/firewall` includes a hook that runs `/data/startup.sh` on boot
2. `/data/startup.sh` calls individual service scripts from `/data/services/`
3. Each service script creates symlinks and starts the service via `/etc/init.d/<service>`

### Service Directories

- **core/**: System customizations (nginx proxy config, environment variables)
- **adguard/**: AdGuard Home DNS server (DNS filtering, ad blocking)
- **v2raya/**: V2rayA proxy service with Xray core (transparent proxy)
- **filebrowser/**: Docker-based file browser (access router files via web)

### Key Router Paths

| Path | Purpose |
|------|---------|
| `/etc/config/` | OpenWrt UCI configuration files |
| `/etc/init.d/` | Service startup scripts (procd) |
| `/etc/nginx/conf.d/` | Nginx server configurations |
| `/data/services/` | Custom service startup scripts |
| `/data/usr/bin/` | Custom binaries |
| `/data/usr/log/` | Service logs |
| `/data/usr/share/` | Shared data (xray assets) |

### Symlink Pattern

Services use symlinks to persist configs on USB storage. Example from adguard startup:
```
/etc/adguardhome.yaml -> ${USB_DIR}/System/adGuardHome/adguardhome.yaml
/etc/config/adguardhome -> ${USB_DIR}/System/adGuardHome/etc/config/adguardhome
/etc/init.d/adguardhome -> ${USB_DIR}/System/adGuardHome/etc/init.d/adguardhome
```

## Service Details

### AdGuard Home (DNS)
- Port: 3000 (UI)
- Config: `/etc/adguardhome.yaml`
- Logs: `/data/usr/log/adguardhome/`

### V2rayA (Proxy)
- Port: 2017 (UI)
- Xray assets: `/data/usr/share/xray/`
- Logs: `/data/usr/log/v2raya/`
- Requires disabling `qca-nss-ecm` service for tproxy to work

### Core
- Sets up nginx reverse proxies for friendly URLs (router.lan, adguard.lan, v2raya.lan)
- Configures PATH to include docker binaries and custom scripts

## Important Config Files on Router

| File | Purpose |
|------|---------|
| `/etc/config/network` | Network interfaces (lan, guest, docker, miot) |
| `/etc/config/wireless` | WiFi configuration |
| `/etc/config/firewall` | Firewall rules and startup hooks |
| `/etc/config/dhcp` | DHCP and static IP assignments |
| `/etc/crontabs/root` | Cron jobs |

## Placeholder Convention

Configuration files contain placeholders like `__PERSONAL_N__` and `__COMPANY_N__` that should be replaced with actual values during deployment. Never commit files with real IP addresses, credentials, or sensitive data.
