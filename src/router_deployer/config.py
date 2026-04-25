"""Configuration loading and management."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Configuration error."""
    pass


class Config:
    """Main configuration manager."""

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or self._find_repo_root()
        self._inventory_dir = self.repo_root / "inventory"
        self._backups_dir = self.repo_root / "backups"
        self._config: dict[str, Any] = {}
        self._hosts: dict[str, Any] = {}
        self._dns_records: dict[str, Any] = {}
        self._loaded = False

    @staticmethod
    def _find_repo_root() -> Path:
        """Find repository root by looking for CLAUDE.md or pyproject.toml."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "CLAUDE.md").exists() or (parent / "pyproject.toml").exists():
                return parent
        return current

    def load(self) -> None:
        """Load all configuration files."""
        self._config = self._load_yaml("config.yml", required=True)
        self._hosts = self._load_yaml("hosts.yml", required=False) or {}
        self._dns_records = self._load_yaml("dns_records.yml", required=False) or {}
        self._loaded = True

    def _load_yaml(self, filename: str, required: bool = True) -> dict[str, Any] | None:
        """Load a YAML file from inventory directory."""
        path = self._inventory_dir / filename
        if not path.exists():
            if required:
                raise ConfigError(f"Required config file not found: {path}")
            return None

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def router_address(self) -> str:
        """Router IP address."""
        return str(self._config.get("router", {}).get("address", ""))

    @property
    def router_user(self) -> str:
        """Router SSH user."""
        return self._config.get("router", {}).get("user", "root")

    @property
    def router_usb_dir(self) -> str:
        """Router USB mount directory."""
        return self._config.get("router", {}).get("usb_dir", "")

    @property
    def system_dir(self) -> str:
        """Router system directory on USB."""
        return f"{self.router_usb_dir}/System"

    @property
    def services(self) -> dict[str, Any]:
        """Enabled services configuration."""
        return self._config.get("services", {})

    @property
    def hosts(self) -> dict[str, Any]:
        """Static hosts configuration."""
        return self._hosts

    @property
    def dns_records(self) -> dict[str, Any]:
        """DNS records configuration."""
        return self._dns_records

    @property
    def backups_dir(self) -> Path:
        """Local backups directory."""
        return self._backups_dir

    @property
    def inventory_dir(self) -> Path:
        """Local inventory directory."""
        return self._inventory_dir

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of issues."""
        issues = []

        if not self.router_address:
            issues.append("Router address not configured in inventory/config.yml")

        return issues


# Global config instance
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
