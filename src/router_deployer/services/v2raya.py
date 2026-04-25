"""V2rayA service deployer."""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..connection import SSHConnection
from .base import ServiceDeployer


class V2rayADeployer(ServiceDeployer):
    """Deployer for V2rayA proxy service."""

    def get_remote_dir_name(self) -> str:
        """V2rayA uses 'v2raya' directory name."""
        return "v2raya"

    def _upload_files(self) -> None:
        """Upload V2rayA files to router."""
        self.conn.upload_dir(self.local_service_dir / "etc", f"{self.remote_system_dir}/etc")

        xray_dir = self.local_service_dir / "xray"
        if xray_dir.exists():
            self.conn.upload_dir(xray_dir, f"{self.remote_system_dir}/xray")

    def _create_symlinks(self) -> None:
        """Create symlinks for V2rayA."""
        symlinks = [
            ("/etc/v2raya", f"{self.remote_system_dir}/etc/v2raya"),
            ("/etc/init.d/v2raya", f"{self.remote_system_dir}/etc/init.d/v2raya"),
        ]

        for dest, src in symlinks:
            self.conn.create_symlink(src, dest)

        self.conn.mkdir("/data/usr/share/xray", parents=True)
        self.conn.mkdir("/data/usr/log/v2raya", parents=True)

    def _post_deploy(self) -> None:
        """Enable V2rayA service."""
        super()._post_deploy()
        self.conn.run("/etc/init.d/v2raya enable")

    def _pull_config(self) -> bool:
        """Pull V2rayA config from router."""
        remote_config = "/etc/v2raya"
        local_config = self.local_backup_dir / "v2raya"

        if self.conn.dir_exists(remote_config):
            return self.conn.download_dir(remote_config, local_config)
        return False

    def _push_config(self) -> bool:
        """Push V2rayA config to router."""
        local_config = self.local_backup_dir / "v2raya"
        remote_config = "/etc/v2raya"

        if not local_config.exists():
            return False

        if self.conn.upload_dir(local_config, remote_config):
            return self.restart()
        return False
