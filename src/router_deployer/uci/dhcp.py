"""DHCP configuration handler."""

from __future__ import annotations

from typing import Any

from ..connection import SSHConnection
from .base import UCIConfigHandler


class DHCPHandler(UCIConfigHandler):
    """Handler for /etc/config/dhcp configuration."""

    @property
    def config_name(self) -> str:
        return "dhcp"

    def validate(self, content: str) -> bool:
        """Validate DHCP config content."""
        return "config dnsmasq" in content

    def generate_static_entries(self) -> str:
        """Generate static host entries from inventory/hosts.yml."""
        hosts_config = self.config.hosts
        if not hosts_config or "hosts" not in hosts_config:
            return "# No hosts defined in inventory/hosts.yml"

        sections = []

        for hostname, host_data in hosts_config["hosts"].items():
            section = {
                "type": "host",
                "name": hostname,
                "options": {
                    "mac": host_data.get("mac", ""),
                    "ip": host_data.get("ip", ""),
                    "name": hostname,
                }
            }
            sections.append(section)

        return self.format_uci(sections)

    def generate_adguard_clients(self) -> list[dict[str, Any]]:
        """Generate AdGuard client entries from inventory/hosts.yml."""
        hosts_config = self.config.hosts
        if not hosts_config or "hosts" not in hosts_config:
            return []

        clients = []

        for hostname, host_data in hosts_config["hosts"].items():
            display_name = host_data.get("name", hostname.replace("_", " ").title())

            client = {
                "name": display_name,
                "ids": [host_data.get("mac", "")],
                "use_global_settings": True,
                "filtering_enabled": False,
            }
            clients.append(client)

        return clients

    def get_current_static_hosts(self, conn: SSHConnection) -> dict[str, dict[str, str]]:
        """Get current static host entries from router as dict keyed by name."""
        self.pull(conn)

        hosts = {}
        for section in self._parsed.get("sections", []):
            if section.get("type") == "host":
                name = section.get("name")
                if name:
                    hosts[name] = {
                        "mac": section.get("options", {}).get("mac", ""),
                        "ip": section.get("options", {}).get("ip", ""),
                    }
        return hosts

    def preview_changes(self, conn: SSHConnection) -> dict[str, Any]:
        """Preview what changes would be made to dhcp config.

        Returns:
            dict with keys: to_add, to_update, to_remove, unchanged
        """
        router_hosts = self.get_current_static_hosts(conn)
        inventory_hosts = self.config.hosts.get("hosts", {})

        changes = {
            "to_add": [],
            "to_update": [],
            "to_remove": [],
            "unchanged": [],
        }

        # Check inventory hosts
        for name, data in inventory_hosts.items():
            if name not in router_hosts:
                changes["to_add"].append({
                    "name": name,
                    "mac": data.get("mac"),
                    "ip": data.get("ip"),
                })
            else:
                router_host = router_hosts[name]
                if (router_host.get("mac") != data.get("mac") or
                    router_host.get("ip") != data.get("ip")):
                    changes["to_update"].append({
                        "name": name,
                        "old": router_host,
                        "new": {
                            "mac": data.get("mac"),
                            "ip": data.get("ip"),
                        },
                    })
                else:
                    changes["unchanged"].append(name)

        # Check for hosts on router but not in inventory (orphans)
        for name in router_hosts:
            if name not in inventory_hosts:
                changes["to_remove"].append({
                    "name": name,
                    "mac": router_hosts[name].get("mac"),
                    "ip": router_hosts[name].get("ip"),
                })

        return changes

    def apply_changes(
        self,
        conn: SSHConnection,
        dry_run: bool = False,
        remove_orphans: bool = False,
        restart_dnsmasq: bool = False,
    ) -> dict[str, Any]:
        """Apply changes to router using UCI commands.

        Args:
            conn: SSH connection to router
            dry_run: If True, only preview changes
            remove_orphans: If True, remove hosts not in inventory
            restart_dnsmasq: If True, restart dnsmasq after changes

        Returns:
            dict with keys: added, updated, removed, failed
        """
        changes = self.preview_changes(conn)
        applied: dict[str, Any] = {"added": [], "updated": [], "removed": [], "failed": []}

        if dry_run:
            return changes

        # Add new hosts
        for host in changes["to_add"]:
            try:
                name = host["name"]
                conn.run(f"uci set dhcp.{name}=host", check=True)
                conn.run(f"uci set dhcp.{name}.mac='{host['mac']}'", check=True)
                conn.run(f"uci set dhcp.{name}.ip='{host['ip']}'", check=True)
                conn.run(f"uci set dhcp.{name}.name='{name}'", check=True)
                applied["added"].append(name)
            except Exception as e:
                applied["failed"].append({"name": name, "error": str(e)})

        # Update existing hosts
        for host in changes["to_update"]:
            try:
                name = host["name"]
                new = host["new"]
                conn.run(f"uci set dhcp.{name}.mac='{new['mac']}'", check=True)
                conn.run(f"uci set dhcp.{name}.ip='{new['ip']}'", check=True)
                applied["updated"].append(name)
            except Exception as e:
                applied["failed"].append({"name": name, "error": str(e)})

        # Remove orphan hosts
        if remove_orphans:
            for host in changes["to_remove"]:
                try:
                    name = host["name"]
                    conn.run(f"uci delete dhcp.{name}", check=True)
                    applied["removed"].append(name)
                except Exception as e:
                    applied["failed"].append({"name": name, "error": str(e)})

        # Commit changes if any were made
        if applied["added"] or applied["updated"] or applied["removed"]:
            conn.run("uci commit dhcp", check=True)

            if restart_dnsmasq:
                conn.run("service dnsmasq restart", check=False)

        return applied
