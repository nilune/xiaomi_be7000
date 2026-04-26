"""Configuration loading and management."""

from __future__ import annotations

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
        self._config_path = self.repo_root / "config.yml"
        self._backups_dir = self.repo_root / "backups"
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
        """Load all configuration files."""
        if self._config_path.exists():
            with open(self._config_path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            raise ConfigError(f"Config file not found: {self._config_path}")

        self._loaded = True

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
        return {"hosts": self._config.get("hosts", {})}

    @property
    def backups_dir(self) -> Path:
        """Local backups directory."""
        return self._backups_dir

    def get_service_config(self, service_name: str) -> dict[str, Any]:
        """Get service-specific configuration from config.yml."""
        return self._config.get("services", {}).get(service_name, {})

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of issues."""
        issues = []

        if not self.router_address:
            issues.append("Router address not configured in config.yml")

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
