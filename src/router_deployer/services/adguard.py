"""AdGuard Home service deployer."""

from __future__ import annotations

from .base import ServiceDeployer


class AdGuardDeployer(ServiceDeployer):
    """Deployer for AdGuard Home DNS server."""

    service_name = "adguard"
    system_subdir = "adGuardHome"
    startup_script_name = "adguardhome.sh"

    def _upload_files(self) -> None:
        """Upload AdGuard Home files to router."""
        self._upload_system_dir()
        self._upload_startup_script()

    def _post_deploy(self) -> None:
        """Enable AdGuard Home service."""
        self.conn.run("/etc/init.d/adguardhome enable", check=False)
