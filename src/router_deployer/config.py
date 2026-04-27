"""Configuration loading and management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Configuration error."""


class Config:
    """Main configuration manager."""

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or self._find_repo_root()
        self._config_path = self.repo_root / "config.yml"
        self._init_dir = self.repo_root / "init"
        self._sync_dir = self.repo_root / "sync"
        self._config: dict[str, Any] = {}
        self._loaded = False

    @staticmethod
    def _find_repo_root() -> Path:
        """Find repository root by looking for config.yml or pyproject.toml."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "config.yml").exists() or (parent / "pyproject.toml").exists():
                return parent
        return current

    def load(self) -> None:
        """Load configuration file."""
        if not self._config_path.exists():
            raise ConfigError(f"Config file not found: {self._config_path}")

        with open(self._config_path, encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        self._loaded = True

    @property
    def router_address(self) -> str:
        """Router IP address."""
        return str(self._config.get("router", {}).get("address", "")).strip()

    @property
    def router_user(self) -> str:
        """Router SSH user."""
        return str(self._config.get("router", {}).get("user", "root")).strip() or "root"

    @property
    def router_usb_dir(self) -> str:
        """Router USB mount directory."""
        return str(self._config.get("router", {}).get("usb_dir", "")).strip()

    @property
    def system_dir(self) -> str:
        """Router system directory on USB."""
        return f"{self.router_usb_dir}/System".rstrip("/")

    @property
    def services(self) -> dict[str, Any]:
        """Enabled services configuration."""
        return self._config.get("services", {})

    @property
    def init_dir(self) -> Path:
        """Initial managed repository state."""
        return self._init_dir

    @property
    def sync_dir(self) -> Path:
        """Local synchronized router state."""
        return self._sync_dir

    def get_service_config(self, service_name: str) -> dict[str, Any]:
        """Get service-specific configuration from config.yml."""
        return self.services.get(service_name, {})

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of issues."""
        issues = []

        if not self.router_address:
            issues.append("Router address not configured in config.yml")

        if not self.router_usb_dir:
            issues.append("Router USB directory not configured in config.yml")

        if not self.init_dir.exists():
            issues.append(f"Missing init directory: {self.init_dir}")

        return issues


_config: Config | None = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
        _config.load()
    return _config


def reload_config() -> Config:
    """Reload configuration from files."""
    global _config
    _config = Config()
    _config.load()
    return _config
