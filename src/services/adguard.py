"""AdGuard Home service deployer."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from services.base import ServiceDeployer
from services.downloads import download_file, extract_tar_member

console = Console()


class AdGuardDeployer(ServiceDeployer):
    """Deployer for AdGuard Home DNS server."""

    service_name = "adguard"
    system_subdir = "adGuardHome"
    startup_script_name = "adguardhome.sh"
    startup_service_name = "AdGuard Home"

    @property
    def binary_version(self) -> str:
        """Desired AdGuard Home version from config."""
        return str(self.config.get_service_config("adguard").get("version", "0.107.74")).strip()

    @property
    def local_binary_path(self) -> Path:
        """Cached AdGuard Home binary."""
        archive = self.cache_dir / self.binary_version / "AdGuardHome_linux_arm64.tar.gz"
        download_file(
            f"https://github.com/AdguardTeam/AdGuardHome/releases/download/v{self.binary_version}/AdGuardHome_linux_arm64.tar.gz",
            archive,
        )
        return extract_tar_member(
            archive,
            "AdGuardHome/AdGuardHome",
            self.cache_dir / self.binary_version / "AdGuardHome",
        )

    @property
    def remote_binary_path(self) -> str:
        """Remote AdGuard Home binary location."""
        return f"{self.remote_system_dir}/usr/bin/AdGuardHome"

    @property
    def remote_version_path(self) -> str:
        """Remote version marker for AdGuard Home."""
        return f"{self.remote_system_dir}/usr/bin/AdGuardHome.version"

    def _upload_files(self) -> None:
        """Upload AdGuard Home files to router."""
        self._upload_system_dir()
        self._upload_startup_script()
        self._upload_binary_if_needed()

    def _post_deploy(self) -> None:
        """Enable AdGuard Home service and reload nginx."""
        self.conn.run("/etc/init.d/adguardhome enable", check=False)
        # Validate and reload nginx to apply the proxy config
        if not self._validate_nginx_config():
            console.print("[yellow]Warning: nginx configuration validation failed[/yellow]")
        else:
            self._reload_nginx()

    def disable(self) -> None:
        """Stop AdGuard Home without deleting its files."""
        self.conn.run("/etc/init.d/adguardhome stop", check=False)
        self.conn.run("/etc/init.d/adguardhome disable", check=False)

    def preview_disable(self) -> list[str]:
        """Describe what disable() would do."""
        return ["/etc/init.d/adguardhome stop", "/etc/init.d/adguardhome disable"]

    def extra_local_paths(self) -> list[Path]:
        """Expose cached binary path in dry-run output."""
        return [self.local_binary_path]

    def _upload_binary_if_needed(self) -> None:
        """Upload AdGuard Home only when version changed or binary is missing."""
        current_version = (self.read_remote_text(self.remote_version_path) or "").strip()
        if (
            current_version == self.binary_version
            and self.conn.file_exists(self.remote_binary_path)
        ):
            return

        self.conn.mkdir(f"{self.remote_system_dir}/usr/bin", parents=True)
        self.conn.upload(self.local_binary_path, self.remote_binary_path)
        self.conn.run(f"chmod +x {self.remote_binary_path}", check=False)
        self.ensure_remote_text(self.remote_version_path, f"{self.binary_version}\n")
