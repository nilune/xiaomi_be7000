"""Network configuration handler."""

from __future__ import annotations

from ..config import Config
from .base import UCIConfigHandler


class NetworkHandler(UCIConfigHandler):
    """Handler for /etc/config/network configuration."""

    @property
    def config_name(self) -> str:
        return "network"

    def validate(self, content: str) -> bool:
        """Validate network config content."""
        return "config interface" in content
