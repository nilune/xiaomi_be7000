"""Wireless configuration handler."""

from __future__ import annotations

from ..config import Config
from .base import UCIConfigHandler


class WirelessHandler(UCIConfigHandler):
    """Handler for /etc/config/wireless configuration."""

    @property
    def config_name(self) -> str:
        return "wireless"

    def validate(self, content: str) -> bool:
        """Validate wireless config content."""
        return "config wifi-device" in content
