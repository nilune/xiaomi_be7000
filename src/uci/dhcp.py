"""DHCP configuration handler."""

from __future__ import annotations

import re
from typing import Any

from connection import SSHConnection
from uci.base import UCIConfigHandler


class DHCPHandler(UCIConfigHandler):
    """Handler for /etc/config/dhcp configuration."""

    @property
    def config_name(self) -> str:
        return "dhcp"

    def validate(self, content: str) -> bool:
        """Validate DHCP config content."""
        return "config dnsmasq" in content

    def list_static_hosts(self, conn: SSHConnection) -> list[dict[str, str]]:
        """Return current static host entries sorted by section name."""
        self.pull(conn)

        hosts = []
        for section in self._parsed.get("sections", []):
            if section.get("type") != "host":
                continue

            options = section.get("options", {})
            hosts.append(
                {
                    "section": section.get("name", ""),
                    "name": options.get("name", section.get("name", "")),
                    "mac": options.get("mac", ""),
                    "ip": options.get("ip", ""),
                }
            )

        return sorted(hosts, key=lambda item: (item["name"], item["section"]))

    def find_hosts(self, conn: SSHConnection, value: str, by: str = "any") -> list[dict[str, str]]:
        """Find static hosts by name, ip, mac, or any field."""
        normalized = value.strip().lower()
        matches = []

        for host in self.list_static_hosts(conn):
            fields = {
                "name": host["name"].lower(),
                "ip": host["ip"].lower(),
                "mac": host["mac"].lower(),
                "section": host["section"].lower(),
            }

            if by == "any":
                if normalized in fields.values():
                    matches.append(host)
            elif by == "name":
                if normalized in {fields["name"], fields["section"]}:
                    matches.append(host)
            elif by in {"ip", "mac", "section"} and fields[by] == normalized:
                matches.append(host)

        return matches

    def add_static_host(
        self,
        conn: SSHConnection,
        *,
        name: str,
        mac: str,
        ip: str,
        replace: bool = False,
        restart_dnsmasq: bool = False,
    ) -> dict[str, Any]:
        """Add or replace a static DHCP host entry."""
        matches = []
        current_hosts = self.list_static_hosts(conn)
        for host in current_hosts:
            if host["name"].lower() == name.lower() or host["mac"].lower() == mac.lower() or host["ip"] == ip:
                matches.append(host)

        if matches and not replace:
            return {"added": False, "replaced": [], "conflicts": matches}

        removed_sections = []
        for host in matches:
            conn.run(f"uci delete dhcp.{host['section']}", check=True)
            removed_sections.append(host["section"])

        section_name = self._make_section_name(name)
        conn.run(f"uci set dhcp.{section_name}=host", check=True)
        conn.run(f"uci set dhcp.{section_name}.name='{name}'", check=True)
        conn.run(f"uci set dhcp.{section_name}.mac='{mac.lower()}'", check=True)
        conn.run(f"uci set dhcp.{section_name}.ip='{ip}'", check=True)
        conn.run("uci commit dhcp", check=True)

        if restart_dnsmasq:
            conn.run("service dnsmasq restart", check=False)

        return {"added": True, "section": section_name, "replaced": removed_sections}

    def remove_static_host(
        self,
        conn: SSHConnection,
        *,
        value: str,
        by: str = "any",
        restart_dnsmasq: bool = False,
    ) -> dict[str, Any]:
        """Remove static DHCP entries matched by selector."""
        matches = self.find_hosts(conn, value, by=by)
        if not matches:
            return {"removed": [], "matched": 0}

        removed = []
        for host in matches:
            conn.run(f"uci delete dhcp.{host['section']}", check=True)
            removed.append(host)

        conn.run("uci commit dhcp", check=True)
        if restart_dnsmasq:
            conn.run("service dnsmasq restart", check=False)

        return {"removed": removed, "matched": len(removed)}

    def _make_section_name(self, name: str) -> str:
        """Convert arbitrary host name into a safe UCI section name."""
        section_name = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
        return section_name or "static_host"
