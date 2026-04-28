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
    startup_service_name: str | None = None

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

    @property
    def cache_dir(self) -> Path:
        """Local cache for downloaded release assets."""
        return self.config.repo_root / "tmp" / "downloads" / self.service_name

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
            console.print(
                f"  [blue]_System source:[/blue] {self._display_path(self.local_system_dir)}"
            )
            for file_path in sorted(p for p in self.local_system_dir.rglob("*") if p.is_file()):
                console.print(f"    - {file_path.relative_to(self.local_system_dir)}")

        if self.startup_script_path and self.startup_script_path.exists():
            console.print(
                f"  [blue]Startup script:[/blue] {self._display_path(self.startup_script_path)}"
            )

        for path in self.extra_local_paths():
            console.print(f"  [blue]Extra asset:[/blue] {self._display_path(path)}")

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
        if (
            self.startup_script_path
            and self.startup_script_path.exists()
            and self.remote_startup_script
        ):
            self.conn.mkdir("/data/services", parents=True)
            self.conn.upload(self.startup_script_path, self.remote_startup_script)
            self.conn.run(f"chmod +x {self.remote_startup_script}", check=False)

    def extra_local_paths(self) -> list[Path]:
        """Additional local files that should be uploaded."""
        return []

    def should_run_from_startup(self) -> bool:
        """Whether startup.sh should invoke this service."""
        return bool(self.startup_script_name and self.startup_service_name)

    def startup_invocation_line(self) -> str | None:
        """Return the canonical startup.sh invocation line for the service."""
        if not self.should_run_from_startup() or not self.remote_startup_script:
            return None
        return f'    run_service "{self.startup_service_name}" "{self.remote_startup_script}"'

    def disable(self) -> None:
        """Disable the service on the router without deleting its data."""
        return None

    def preview_disable(self) -> list[str]:
        """Describe what disable() would do."""
        return []

    def read_remote_text(self, path: str) -> str | None:
        """Read a remote file when it exists."""
        if not self.conn.file_exists(path):
            return None
        return self.conn.read_file(path)

    def ensure_remote_text(self, path: str, content: str) -> None:
        """Write text to a remote file without creating a backup."""
        self.conn.write_file(path, content, backup=False)

    def _display_path(self, path: Path) -> Path | str:
        """Render a path relative to the repo root when possible."""
        try:
            return path.relative_to(self.config.repo_root)
        except ValueError:
            return path

    def _validate_nginx_config(self) -> bool:
        """Validate nginx configuration. Returns True if valid or nginx not present."""
        try:
            self.conn.run("nginx -t", check=True)
            return True
        except Exception:
            return False

    def _reload_nginx(self) -> bool:
        """Reload nginx gracefully. Returns True on success."""
        if not self.conn.file_exists("/etc/init.d/nginx"):
            return True
        try:
            self.conn.run("service nginx reload", check=True)
            return True
        except Exception:
            return False

    @abstractmethod
    def _upload_files(self) -> None:
        """Upload service files to router."""

    def _post_deploy(self) -> None:
        """Post-deployment actions."""
        return None
