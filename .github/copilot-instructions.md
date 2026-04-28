# Copilot Instructions for router-deployer

This is a Python deployment and configuration management tool for the Xiaomi BE7000 router, providing automated service deployment, state synchronization, and DHCP management.

## Quick Start

### Setup

```bash
# Using uv (modern Python package manager):
uv sync

# Using pip:
pip install -e .

# Activate virtual environment (if using venv):
source .venv/bin/activate
```

### Build & Lint

```bash
# Lint the codebase (required before commits)
ruff check src/
ruff format src/

# Install with dev dependencies to get ruff
uv sync --extra dev

# Build the package for distribution
uv build
```

### Running the CLI

The main entry point is `router` command (installed via `[project.scripts]` in pyproject.toml):

```bash
# Show help for all commands
uv run router --help

# Examples:
uv run router config show
uv run router config validate
uv run router deploy run startup
uv run router sync pull
uv run router dhcp hosts
```

## Architecture Overview

This is a three-layer system managing Xiaomi BE7000 configuration:

### **Layers**

1. **`doc/`** – Documentation and manual setup guides for services (AdGuard, V2rayA, Core, FileBrowser)
2. **`init/`** – Committed "golden image" files for initial deployment (safe to auto-apply to new routers)
3. **`sync/`** – Local mirror of live router state, **not committed** to git

### **File Organization**

- **System config files** (only these four are managed in sync):
  - `sync/etc/config/dhcp` ← `/etc/config/dhcp`
  - `sync/etc/config/firewall` ← `/etc/config/firewall`
  - `sync/etc/config/network` ← `/etc/config/network`
  - `sync/etc/config/wireless` ← `/etc/config/wireless`

- **Service-specific state** (never stored in `/etc`):
  - `sync/_System/<service>/` ← `${ROUTER_USB_DIR}/System/<service>/`
  - Examples: `_System/adGuardHome/`, `_System/v2raya/`, `_System/filebrowser/`, etc.

- **Scripts**:
  - `sync/data/` ← `/data/` (startup.sh, service scripts, helper scripts)

### **Key Principle**

Manual system config changes (UCI files) remain **out of scope for automation**. Only DHCP static hosts, startup scripts, and service-specific files in `_System/` are automated. This prevents breaking hand-tuned firewall rules or network configs.

## Code Structure

All Python code lives directly in `src/` (no nested packages):

- **`src/cli.py`** – Click-based command groups (config, deploy, sync, dhcp, utils)
- **`src/config.py`** – YAML loading with validation; finds repo root via config.yml or pyproject.toml
- **`src/connection.py`** – SSH/SCP wrappers for router communication
- **`src/sync.py`** – Sync pull/push logic with explicit managed path lists
- **`src/services/`** – Service deployers (core, adguard, v2raya, filebrowser, docker, downloads)
- **`src/uci/`** – UCI config file parsers and handlers (dhcp, firewall, network, wireless, base)

## Configuration

Create `config.yml` from `config.yml.example`:

```yaml
router:
  address: 192.168.31.1
  user: root
  usb_dir: /mnt/usb-ef8d1024

services:
  core:
    enabled: true
  adguard:
    enabled: true
    version: 0.107.74
  v2raya:
    enabled: true
    version: 2.2.7.5
    xray_version: 26.4.15
  filebrowser:
    enabled: false
    version: latest
    port: 8088
```

Router SSH password must be set via `ROUTER_SSH_PASSWORD` environment variable or `.env` file.

## Deployment Flow

**`deploy run startup`** (or alias `deploy run base`):
1. Reads `config.yml`
2. Copies `/data/startup.sh` to router
3. For each **enabled** service: copies initial files to `_System/<service>/`
4. Downloads/verifies service binaries (AdGuard, V2rayA, xray) if versions mismatch
5. For Docker services: recreates containers with `--restart unless-stopped`
6. Copies service startup scripts to `/data/services/` and `/data/scripts/`
7. **Does NOT touch** system UCI files (`/etc/config/dhcp`, firewall, network, wireless)

**`deploy run base`** is an alias for `deploy run startup`.

**`enabled: false`** stops the service (removes from startup.sh or deletes Docker container) but preserves data.

## Sync Flow

**`sync pull`** – Copies from router → local `sync/` directory
**`sync push`** – Copies from local `sync/` directory → router

Both work with an **explicit managed path list** to avoid noise and keep `_System/` as the source of truth for service configs.

**Not pulled/pushed**:
- `/etc/init.d/*` (symlinks to `_System`)
- `/etc/nginx/conf.d/*` (runtime-generated)
- `/etc/profile.d/*` (system-level)
- `/etc/v2raya`, `/etc/xray`, `/etc/adguardhome.yaml` (symlinks to or live in `_System`)

## DHCP Management

DHCP static hosts are managed directly from UCI:

```bash
router dhcp leases              # Show current DHCP leases
router dhcp hosts               # Show static hosts
router dhcp candidates          # Show devices not yet in static hosts
router dhcp add <name> <mac> <ip>
router dhcp remove <value> --by name|ip|mac|section
```

No separate `inventory/hosts.yml` – the router's `/etc/config/dhcp` is the source of truth.

Candidates can be filtered via `config.yml`:
```yaml
dhcp:
  static_candidates:
    exclude_macs: []
    exclude_mac_prefixes: ["ec:fa:bc"]
```

## Key Conventions

1. **Repository root discovery** – Found via `config.yml` or `pyproject.toml` in current or parent directories
2. **Path handling** – All paths are `pathlib.Path` objects; relative paths resolve from repo root
3. **Error handling** – SSH/connection errors exit with status 1 and display readable messages
4. **Output** – Uses `rich` for styled console output (tables, colored text)
5. **Linting** – Ruff with lines-of-100 characters, Python 3.10+, rules: E, F, W, I, N, UP, B, C4
6. **Type hints** – Use `from __future__ import annotations` and full type hints throughout
7. **Environment variables** – Loaded from `.env` via `python-dotenv`

## Common Tasks

### Add a new service deployer

1. Create `src/services/myservice.py` inheriting from `ServiceDeployer` (see `src/services/base.py`)
2. Register in `src/services/__init__.py` in `SERVICE_DEPLOYERS`
3. Add config schema to `config.yml.example`
4. Add documentation to `doc/myservice.md`

### Modify sync rules

Edit `src/sync.py` where `SYNC_RULES` is defined. Add entries to specify source and destination paths for sync pull/push.

### Update UCI parsing

Edit files in `src/uci/` (dhcp.py, firewall.py, network.py, wireless.py) to add new UCI block or option handling.

## Testing

Currently no automated test suite. Validate with:

```bash
ruff check src/
uv run router config validate  # Checks SSH connectivity and config validity
```

Run linter before committing; all Python files must pass Ruff checks.

## Dependencies

**Runtime:**
- `click` – CLI framework
- `pyyaml` – Config file parsing
- `python-dotenv` – Environment variable loading
- `bcrypt` – (prepare for) password hashing
- `rich` – Styled console output

**Dev:**
- `ruff` – Linting and formatting

Managed via `uv` (lock file: `uv.lock`). For pip-only: `pip install -e .` and `pip install -e ".[dev]"`.

## Deployment Notes

The repo is built as a wheel via hatchling. Installation creates a `router` command on the system PATH.

Only these files are included in the wheel:
```
src/cli.py
src/config.py
src/connection.py
src/sync.py
src/services/
src/uci/
```

The `init/`, `sync/`, `doc/` directories and git files are excluded and only live in the repo.

## Environment

- **Requires:** Python ≥3.10
- **Tested on:** macOS, Linux (router runs OpenWrt, not the Python environment)
- **SSH access:** To router via `ROUTER_SSH_PASSWORD` environment variable
