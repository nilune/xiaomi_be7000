"""Firewall configuration handler."""

from __future__ import annotations

from ..config import Config
from .base import UCIConfigHandler


class FirewallHandler(UCIConfigHandler):
    """Handler for /etc/config/firewall configuration."""

    @property
    def config_name(self) -> str:
        return "firewall"

    def validate(self, content: str) -> bool:
        """Validate firewall config content."""
        return "config defaults" in content
