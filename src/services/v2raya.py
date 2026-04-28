"""V2rayA service deployer."""

from __future__ import annotations

from pathlib import Path

from services.base import ServiceDeployer
from services.downloads import download_file, extract_zip_member


class V2rayADeployer(ServiceDeployer):
    """Deployer for V2rayA proxy service."""

    service_name = "v2raya"
    system_subdir = "v2raya"
    startup_script_name = "v2raya.sh"
    startup_service_name = "V2rayA (with XRay)"

    @property
    def v2raya_version(self) -> str:
        """Desired v2rayA version from config."""
        return str(self.config.get_service_config("v2raya").get("version", "2.2.7.5")).strip()

    @property
    def xray_version(self) -> str:
        """Desired Xray version from config."""
        return str(self.config.get_service_config("v2raya").get("xray_version", "26.4.15")).strip()

    @property
    def local_v2raya_path(self) -> Path:
        """Cached v2rayA binary."""
        destination = self.cache_dir / "v2raya" / self.v2raya_version / "v2raya"
        url = (
            "https://github.com/v2rayA/v2rayA/releases/download/"
            f"v{self.v2raya_version}/v2raya_linux_arm64_{self.v2raya_version}"
        )
        return download_file(url, destination)

    @property
    def local_xray_path(self) -> Path:
        """Cached Xray binary."""
        archive = self.cache_dir / "xray" / self.xray_version / "Xray-linux-arm64-v8a.zip"
        download_file(
            f"https://github.com/XTLS/Xray-core/releases/download/v{self.xray_version}/Xray-linux-arm64-v8a.zip",
            archive,
        )
        return extract_zip_member(
            archive,
            "xray",
            self.cache_dir / "xray" / self.xray_version / "xray",
        )

    def extra_local_paths(self) -> list[Path]:
        """Additional helper scripts shipped with the service."""
        return [
            self.config.init_dir / "data" / "scripts" / "update_geo_files.sh",
            self.local_v2raya_path,
            self.local_xray_path,
        ]

    def _upload_files(self) -> None:
        """Upload V2rayA files to router."""
        self._upload_system_dir()
        self._upload_startup_script()
        self._upload_binaries_if_needed()

        geo_script = self.config.init_dir / "data" / "scripts" / "update_geo_files.sh"
        if geo_script.exists():
            self.conn.mkdir("/data/scripts", parents=True)
            self.conn.upload(geo_script, "/data/scripts/update_geo_files.sh")
            self.conn.run("chmod +x /data/scripts/update_geo_files.sh", check=False)

    def _post_deploy(self) -> None:
        """Enable V2rayA service."""
        self.conn.run("/etc/init.d/v2raya enable", check=False)

    def disable(self) -> None:
        """Stop V2rayA without deleting its files."""
        self.conn.run("/etc/init.d/v2raya stop", check=False)
        self.conn.run("/etc/init.d/v2raya disable", check=False)

    def preview_disable(self) -> list[str]:
        """Describe what disable() would do."""
        return ["/etc/init.d/v2raya stop", "/etc/init.d/v2raya disable"]

    def _upload_binaries_if_needed(self) -> None:
        """Upload v2rayA and Xray only when versions changed."""
        self.conn.mkdir(f"{self.remote_system_dir}/usr/bin", parents=True)
        self._upload_binary_if_needed(
            local_path=self.local_v2raya_path,
            remote_path=f"{self.remote_system_dir}/usr/bin/v2raya",
            version_path=f"{self.remote_system_dir}/usr/bin/v2raya.version",
            version=self.v2raya_version,
        )
        self._upload_binary_if_needed(
            local_path=self.local_xray_path,
            remote_path=f"{self.remote_system_dir}/usr/bin/xray",
            version_path=f"{self.remote_system_dir}/usr/bin/xray.version",
            version=self.xray_version,
        )

    def _upload_binary_if_needed(
        self,
        *,
        local_path: Path,
        remote_path: str,
        version_path: str,
        version: str,
    ) -> None:
        """Upload one binary if the router does not already have the requested version."""
        current_version = (self.read_remote_text(version_path) or "").strip()
        if current_version == version and self.conn.file_exists(remote_path):
            return

        self.conn.upload(local_path, remote_path)
        self.conn.run(f"chmod +x {remote_path}", check=False)
        self.ensure_remote_text(version_path, f"{version}\n")
