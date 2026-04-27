"""Base service deployer class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from rich.console import Console

from config import Config
from connection import SSHConnection

console = Console()


class ServiceDeployer(ABC):
    """Base class for service deployers."""

    service_name: str = ""
    system_subdir: str = ""
    startup_script_name: str | None = None

    def __init__(self, config: Config, conn: SSHConnection):
        self.config = config
        self.conn = conn

    @property
    def local_system_dir(self) -> Path:
        """Local init directory for a service inside _System."""
        if not self.system_subdir:
            return self.config.init_dir / "_System"
        return self.config.init_dir / "_System" / self.system_subdir

    @property
    def remote_system_dir(self) -> str:
        """Remote service directory on USB."""
        return f"{self.config.system_dir}/{self.system_subdir}".rstrip("/")

    @property
    def startup_script_path(self) -> Path | None:
        """Local startup script path."""
        if not self.startup_script_name:
            return None
        return self.config.init_dir / "data" / "services" / self.startup_script_name

    @property
    def remote_startup_script(self) -> str | None:
        """Remote startup script path."""
        if not self.startup_script_name:
            return None
        return f"/data/services/{self.startup_script_name}"

    def deploy(self, dry_run: bool = False) -> bool:
        """Deploy service to router."""
        if dry_run:
            self._preview_deploy()
            return True

        self._pre_deploy()
        self._upload_files()
        self._post_deploy()
        return True

    def _preview_deploy(self) -> None:
        """Show what would be done in a dry run."""
        console.print(f"  [blue]Service:[/blue] {self.service_name}")
        if self.system_subdir and self.local_system_dir.exists():
            console.print(f"  [blue]_System source:[/blue] {self.local_system_dir}")
            for file_path in sorted(p for p in self.local_system_dir.rglob("*") if p.is_file()):
                console.print(f"    - {file_path.relative_to(self.local_system_dir)}")

        if self.startup_script_path and self.startup_script_path.exists():
            console.print(f"  [blue]Startup script:[/blue] {self.startup_script_path}")

        for path in self.extra_local_paths():
            console.print(f"  [blue]Extra asset:[/blue] {path}")

    def _pre_deploy(self) -> None:
        """Pre-deployment validation."""
        if self.system_subdir and not self.local_system_dir.exists():
            raise FileNotFoundError(f"Service directory not found: {self.local_system_dir}")

    def _upload_system_dir(self) -> None:
        """Upload the full managed _System service directory."""
        if not self.system_subdir:
            return
        self.conn.mkdir(self.config.system_dir, parents=True)
        self.conn.upload_dir_exact(self.local_system_dir, self.remote_system_dir)

    def _upload_startup_script(self) -> None:
        """Upload the startup script if the service has one."""
        if self.startup_script_path and self.startup_script_path.exists() and self.remote_startup_script:
            self.conn.mkdir("/data/services", parents=True)
            self.conn.upload(self.startup_script_path, self.remote_startup_script)
            self.conn.run(f"chmod +x {self.remote_startup_script}", check=False)

    def extra_local_paths(self) -> list[Path]:
        """Additional local files that should be uploaded."""
        return []

    @abstractmethod
    def _upload_files(self) -> None:
        """Upload service files to router."""

    def _post_deploy(self) -> None:
        """Post-deployment actions."""
