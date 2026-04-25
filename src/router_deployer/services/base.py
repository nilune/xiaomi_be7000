"""Base service deployer class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rich.console import Console

from ..config import Config
from ..connection import SSHConnection

console = Console()


class ServiceDeployer(ABC):
    """Base class for service deployers."""

    def __init__(self, config: Config, conn: SSHConnection):
        self.config = config
        self.conn = conn
        self.name = self.__class__.__name__.replace("Deployer", "").lower()

    @property
    def local_service_dir(self) -> Path:
        """Local service directory (e.g., ./adguard, ./v2raya)."""
        return self.config.repo_root / self.name

    @property
    def local_backup_dir(self) -> Path:
        """Local backup directory for this service."""
        return self.config.backups_dir / self.name

    @property
    def remote_system_dir(self) -> str:
        """Remote system directory on USB."""
        return f"{self.config.system_dir}/{self.get_remote_dir_name()}"

    def get_remote_dir_name(self) -> str:
        """Get the remote directory name (may differ from service name)."""
        return self.name

    def deploy(self, dry_run: bool = False) -> bool:
        """Deploy service to router."""
        if dry_run:
            return self._preview_deploy()

        self._pre_deploy()
        self.conn.mkdir(self.remote_system_dir, parents=True)
        self._upload_files()
        self._create_symlinks()
        self._post_deploy()
        return True

    def _preview_deploy(self) -> bool:
        """Show what would be done in a dry run."""
        console.print(f"  [blue]Service directory:[/blue] {self.local_service_dir}")
        console.print(f"  [blue]Remote path:[/blue] {self.remote_system_dir}")

        if self.local_service_dir.exists():
            console.print(f"  [blue]Files to upload:[/blue]")
            for f in self.local_service_dir.rglob("*"):
                if f.is_file():
                    rel_path = f.relative_to(self.local_service_dir)
                    console.print(f"    - {rel_path}")
        else:
            console.print(f"  [yellow]Service directory not found[/yellow]")

        return True

    @abstractmethod
    def _upload_files(self) -> None:
        """Upload service files to router."""
        pass

    @abstractmethod
    def _create_symlinks(self) -> None:
        """Create symlinks on router."""
        pass

    def _pre_deploy(self) -> None:
        """Pre-deployment validation."""
        if not self.local_service_dir.exists():
            raise FileNotFoundError(f"Service directory not found: {self.local_service_dir}")

    def _post_deploy(self) -> None:
        """Post-deployment actions."""
        local_startup = self.local_service_dir / "startup.sh"
        if local_startup.exists():
            remote_startup = f"/data/services/{self.name}.sh"
            self.conn.upload(local_startup, remote_startup)
            self.conn.run(f"chmod +x {remote_startup}")

    def pull(self) -> bool:
        """Pull configuration from router to local backup."""
        self.local_backup_dir.mkdir(parents=True, exist_ok=True)
        return self._pull_config()

    @abstractmethod
    def _pull_config(self) -> bool:
        """Pull service-specific config."""
        pass

    def push(self, dry_run: bool = False) -> bool:
        """Push local configuration to router."""
        if not self.local_backup_dir.exists():
            raise FileNotFoundError(f"No local backup found: {self.local_backup_dir}")

        if dry_run:
            return True

        return self._push_config()

    @abstractmethod
    def _push_config(self) -> bool:
        """Push service-specific config."""
        pass

    def restart(self) -> bool:
        """Restart service on router."""
        result = self.conn.run(f"service {self.name} restart", check=False)
        return "error" not in result.lower()

    def status(self) -> str:
        """Get service status."""
        return self.conn.run(f"service {self.name} status", check=False)
