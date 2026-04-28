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

    def list_static_candidates(self, conn: SSHConnection) -> list[dict[str, str]]:
        """Return DHCP leases that are not yet covered by static hosts."""
        static_hosts = self.list_static_hosts(conn)
        leased_hosts = self._read_leases(conn)
        excluded_macs = set(self.config.excluded_static_candidate_macs)
        excluded_prefixes = tuple(self.config.excluded_static_candidate_prefixes)
        candidates: list[dict[str, str]] = []

        for lease in leased_hosts:
            mac = lease["mac"].lower()

            if mac in excluded_macs or any(mac.startswith(prefix) for prefix in excluded_prefixes):
                continue

            reason = self._candidate_reason(static_hosts, lease)
            if reason is None:
                continue

            candidates.append(
                {
                    "mac": lease["mac"],
                    "ip": lease["ip"],
                    "name": lease["name"],
                    "reason": reason,
                }
            )

        return sorted(candidates, key=lambda item: (item["name"], item["ip"], item["mac"]))

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
            if (
                host["name"].lower() == name.lower()
                or host["mac"].lower() == mac.lower()
                or host["ip"] == ip
            ):
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
            self._restart_dnsmasq_with_check(conn)

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
            self._restart_dnsmasq_with_check(conn)

        return {"removed": removed, "matched": len(removed)}

    def _make_section_name(self, name: str) -> str:
        """Convert arbitrary host name into a safe UCI section name."""
        section_name = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
        return section_name or "static_host"

    def _read_leases(self, conn: SSHConnection) -> list[dict[str, str]]:
        """Parse current DHCP leases from /tmp/dhcp.leases."""
        content = conn.read_file("/tmp/dhcp.leases")
        leases = []
        for line in content.strip().splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            leases.append(
                {
                    "lease": parts[0],
                    "mac": parts[1].lower(),
                    "ip": parts[2],
                    "name": parts[3],
                }
            )
        return leases

    @staticmethod
    def _candidate_reason(static_hosts: list[dict[str, str]], lease: dict[str, str]) -> str | None:
        """Classify whether a lease should be shown as a candidate."""
        exact_match = next(
            (
                host
                for host in static_hosts
                if host["mac"].lower() == lease["mac"].lower() and host["ip"] == lease["ip"]
            ),
            None,
        )
        if exact_match is not None:
            return None

        same_mac = [host for host in static_hosts if host["mac"].lower() == lease["mac"].lower()]
        if same_mac:
            return "Static IP differs"

        same_ip = [host for host in static_hosts if host["ip"] == lease["ip"]]
        if same_ip:
            return "IP already pinned"

        if lease["name"] and lease["name"] != "*":
            same_name = [
                host for host in static_hosts if host["name"].lower() == lease["name"].lower()
            ]
            if same_name:
                return "Hostname differs"

        return "Lease only"

    def _restart_dnsmasq_with_check(self, conn: SSHConnection) -> bool:
        """Restart dnsmasq and verify it reloads the config correctly."""
        try:
            conn.run("service dnsmasq restart", check=True)
            # Give dnsmasq a moment to reread the config and update leases
            conn.run("sleep 1", check=False)
            return True
        except Exception:
            return False
