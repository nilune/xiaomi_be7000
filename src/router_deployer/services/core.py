"""Core system deployer."""

from __future__ import annotations

from ..config import Config
from ..connection import SSHConnection
from .base import ServiceDeployer


class CoreDeployer(ServiceDeployer):
    """Deployer for core system configurations (nginx, env vars)."""

    def _upload_files(self) -> None:
        """Upload core system files to router."""
        nginx_dir = self.local_service_dir / "etc" / "nginx" / "conf.d"
        if nginx_dir.exists():
            for f in nginx_dir.glob("*.conf"):
                self.conn.upload(f, f"/etc/nginx/conf.d/{f.name}")

    def _create_symlinks(self) -> None:
        """No symlinks needed for core."""
        pass

    def _pull_config(self) -> bool:
        """Pull nginx configs from router."""
        import subprocess

        self.local_backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.conn.download_dir("/etc/nginx/conf.d", self.local_backup_dir / "nginx")
            return True
        except Exception:
            return False

    def _push_config(self) -> bool:
        """Push nginx configs to router."""
        local_nginx = self.local_backup_dir / "nginx"
        if not local_nginx.exists():
            return False

        return self.conn.upload_dir(local_nginx, "/etc/nginx/conf.d")
