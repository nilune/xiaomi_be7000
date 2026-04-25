"""AdGuard Home service deployer."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..connection import SSHConnection
from .base import ServiceDeployer


class AdGuardDeployer(ServiceDeployer):
    """Deployer for AdGuard Home DNS server."""

    def get_remote_dir_name(self) -> str:
        """AdGuard uses 'adGuardHome' directory name."""
        return "adGuardHome"

    def _upload_files(self) -> None:
        """Upload AdGuard Home files to router."""
        self.conn.upload_dir(self.local_service_dir / "etc", f"{self.remote_system_dir}/etc")

        dns_servers = self.local_service_dir / "dns_servers.txt"
        if dns_servers.exists():
            self.conn.upload(dns_servers, f"{self.remote_system_dir}/dns_servers.txt")

    def _create_symlinks(self) -> None:
        """Create symlinks for AdGuard Home."""
        symlinks = [
            ("/etc/adguardhome.yaml", f"{self.remote_system_dir}/adguardhome.yaml"),
            ("/etc/config/adguardhome", f"{self.remote_system_dir}/etc/config/adguardhome"),
            ("/etc/init.d/adguardhome", f"{self.remote_system_dir}/etc/init.d/adguardhome"),
        ]

        for dest, src in symlinks:
            self.conn.create_symlink(src, dest)

        self.conn.run(f"touch {self.remote_system_dir}/adguardhome.yaml")
        self.conn.mkdir(f"{self.remote_system_dir}/log", parents=True)

    def _post_deploy(self) -> None:
        """Enable AdGuard Home service."""
        super()._post_deploy()
        self.conn.run("/etc/init.d/adguardhome enable")

    def _pull_config(self) -> bool:
        """Pull AdGuard Home config from router."""
        remote_config = "/etc/adguardhome.yaml"
        local_config = self.local_backup_dir / "adguardhome.yaml"

        if self.conn.file_exists(remote_config):
            return self.conn.download(remote_config, local_config)
        return False

    def _push_config(self) -> bool:
        """Push AdGuard Home config to router."""
        local_config = self.local_backup_dir / "adguardhome.yaml"
        remote_config = "/etc/adguardhome.yaml"

        if not local_config.exists():
            return False

        if self.conn.upload(local_config, remote_config):
            return self.restart()
        return False

    def update_clients_from_inventory(self) -> bool:
        """Update AdGuard clients from inventory/hosts.yml."""
        from ..uci.dhcp import DHCPHandler
        import yaml

        handler = DHCPHandler(self.config)
        clients = handler.generate_adguard_clients()

        self.pull()

        local_config = self.local_backup_dir / "adguardhome.yaml"
        if not local_config.exists():
            return False

        with open(local_config, "r") as f:
            config = yaml.safe_load(f)

        config["clients"] = clients

        with open(local_config, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        return self.push()
