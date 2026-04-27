"""V2rayA service deployer."""

from __future__ import annotations

from pathlib import Path

from services.base import ServiceDeployer


class V2rayADeployer(ServiceDeployer):
    """Deployer for V2rayA proxy service."""

    service_name = "v2raya"
    system_subdir = "v2raya"
    startup_script_name = "v2raya.sh"

    def extra_local_paths(self) -> list[Path]:
        """Additional helper scripts shipped with the service."""
        return [self.config.init_dir / "data" / "scripts" / "update_geo_files.sh"]

    def _upload_files(self) -> None:
        """Upload V2rayA files to router."""
        self._upload_system_dir()
        self._upload_startup_script()

        geo_script = self.config.init_dir / "data" / "scripts" / "update_geo_files.sh"
        if geo_script.exists():
            self.conn.mkdir("/data/scripts", parents=True)
            self.conn.upload(geo_script, "/data/scripts/update_geo_files.sh")
            self.conn.run("chmod +x /data/scripts/update_geo_files.sh", check=False)

    def _post_deploy(self) -> None:
        """Enable V2rayA service."""
        self.conn.run("/etc/init.d/v2raya enable", check=False)
