"""Startup script deployer."""

from __future__ import annotations

from pathlib import Path

from services.base import ServiceDeployer


class StartupDeployer(ServiceDeployer):
    """Deploy the shared /data/startup.sh script."""

    service_name = "startup"

    @property
    def startup_source_path(self) -> Path:
        """Local startup script path."""
        return self.config.init_dir / "data" / "startup.sh"

    def extra_local_paths(self) -> list[Path]:
        """Expose startup.sh in dry-run output."""
        return [self.startup_source_path]

    def _pre_deploy(self) -> None:
        """Validate that startup.sh exists."""
        if not self.startup_source_path.exists():
            raise FileNotFoundError(f"Startup script not found: {self.startup_source_path}")

    def _upload_files(self) -> None:
        """Upload the shared startup script to the router."""
        self.conn.mkdir("/data", parents=True)
        rendered = self._render_startup_script()
        self.conn.write_file("/data/startup.sh", rendered, backup=False)
        self.conn.run("chmod +x /data/startup.sh", check=False)

    def _render_startup_script(self) -> str:
        """Render startup.sh with enabled native services uncommented."""
        content = self.startup_source_path.read_text(encoding="utf-8")

        from services import get_service_deployer

        for service_name in ("core", "adguard", "v2raya", "filebrowser"):
            if service_name == "filebrowser":
                enabled = False
            else:
                enabled = self.config.is_service_enabled(service_name)

            deployer = get_service_deployer(service_name, self.config, self.conn)
            invocation = deployer.startup_invocation_line()
            if not invocation:
                continue

            commented = f"# {invocation.lstrip()}"
            replacement = invocation if enabled else f"    {commented}"
            content = content.replace(invocation, replacement)

        return content
