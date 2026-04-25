"""Base class for UCI configuration handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..config import Config
from ..connection import SSHConnection


class UCIConfigHandler(ABC):
    """Base class for UCI configuration file handlers."""

    def __init__(self, config: Config):
        self.config = config
        self._raw_content: str = ""
        self._parsed: dict[str, Any] = {}

    @property
    @abstractmethod
    def config_name(self) -> str:
        """UCI config file name (e.g., 'dhcp', 'firewall')."""
        pass

    @property
    def remote_path(self) -> str:
        """Full remote path to the config file."""
        return f"/etc/config/{self.config_name}"

    @property
    def local_backup_path(self) -> Path:
        """Local backup path for this config."""
        return self.config.backups_dir / "router" / self.config_name

    def pull(self, conn: SSHConnection) -> str:
        """Pull config from router."""
        self._raw_content = conn.read_file(self.remote_path)
        self._parsed = self._parse_uci(self._raw_content)

        self.local_backup_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_backup_path.write_text(self._raw_content)

        return self._raw_content

    def _parse_uci(self, content: str) -> dict[str, Any]:
        """Parse UCI config format into a dictionary structure."""
        result: dict[str, Any] = {
            "sections": [],
            "named_sections": {}
        }

        current_section: dict[str, Any] | None = None

        for line in content.split("\n"):
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("config "):
                if current_section:
                    result["sections"].append(current_section)

                parts = line[7:].split(None, 1)
                section_type = parts[0]
                section_name = parts[1].strip("'\"") if len(parts) > 1 else None

                current_section = {
                    "type": section_type,
                    "name": section_name,
                    "options": {}
                }

                if section_name:
                    result["named_sections"][section_name] = current_section

            elif line.startswith("option ") and current_section:
                parts = line[7:].split(None, 1)
                if len(parts) == 2:
                    key = parts[0]
                    value = parts[1].strip("'\"")
                    current_section["options"][key] = value

            elif line.startswith("list ") and current_section:
                parts = line[5:].split(None, 1)
                if len(parts) == 2:
                    key = parts[0]
                    value = parts[1].strip("'\"")
                    if key not in current_section["options"]:
                        current_section["options"][key] = []
                    if isinstance(current_section["options"][key], list):
                        current_section["options"][key].append(value)

        if current_section:
            result["sections"].append(current_section)

        return result

    def _format_uci_section(self, section: dict[str, Any]) -> str:
        """Format a section dict back to UCI format."""
        lines = []

        if section.get("name"):
            lines.append(f"config {section['type']} '{section['name']}'")
        else:
            lines.append(f"config {section['type']}")

        for key, value in section.get("options", {}).items():
            if isinstance(value, list):
                for v in value:
                    lines.append(f"\tlist {key} '{v}'")
            else:
                lines.append(f"\toption {key} '{value}'")

        return "\n".join(lines)

    def format_uci(self, sections: list[dict[str, Any]]) -> str:
        """Format multiple sections to UCI config format."""
        return "\n\n".join(self._format_uci_section(s) for s in sections)

    @abstractmethod
    def validate(self, content: str) -> bool:
        """Validate config content before applying."""
        pass


def get_uci_handler(config: Config, name: str) -> UCIConfigHandler:
    """Get UCI handler by name."""
    from .dhcp import DHCPHandler
    from .firewall import FirewallHandler
    from .wireless import WirelessHandler
    from .network import NetworkHandler

    handlers = {
        "dhcp": DHCPHandler,
        "firewall": FirewallHandler,
        "wireless": WirelessHandler,
        "network": NetworkHandler,
    }

    if name not in handlers:
        raise ValueError(f"Unknown UCI config: {name}")

    return handlers[name](config)
