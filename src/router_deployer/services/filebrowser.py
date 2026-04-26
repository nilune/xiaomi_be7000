"""Filebrowser service deployer (Docker-based)."""

from __future__ import annotations

from typing import Any

from .base import ServiceDeployer


class FilebrowserDeployer(ServiceDeployer):
    """Deployer for Filebrowser file manager (Docker)."""

    def get_service_config(self) -> dict[str, Any]:
        """Get filebrowser config from config.yml."""
        return self.config.get_service_config("filebrowser")

    def _upload_files(self) -> None:
        """Upload Filebrowser files to router."""
        if self.local_service_dir.exists():
            settings = self.local_service_dir / "settings.json"
            if settings.exists():
                self.conn.upload(settings, f"{self.remote_system_dir}/settings.json")

    def _create_symlinks(self) -> None:
        """Create symlinks for Filebrowser."""
        pass

    def _post_deploy(self) -> None:
        """Start Filebrowser container."""
        super()._post_deploy()
        self._start_container()

    def _start_container(self) -> None:
        """Start filebrowser Docker container."""
        cfg = self.get_service_config()
        port = cfg.get("port", 8088)
        sources = cfg.get("sources", [])

        # Stop and remove existing container
        self.conn.run("docker stop filebrowser 2>/dev/null || true", check=False)
        self.conn.run("docker rm filebrowser 2>/dev/null || true", check=False)

        # Build volume mounts
        volumes = []
        for source in sources:
            path = source.get("path", "")
            name = source.get("name", "volume")
            if path:
                # Convert path to valid container path
                container_path = f"/srv/{name.lower().replace(' ', '_').replace('-', '_')}"
                volumes.append(f"-v {path}:{container_path}")

        volumes_str = " ".join(volumes) if volumes else ""

        # Run container
        cmd = (
            f"docker run -d "
            f"--name filebrowser "
            f"-p {port}:80 "
            f"{volumes_str} "
            f"--restart unless-stopped "
            f"filebrowser/filebrowser:latest"
        )

        self.conn.run(cmd, check=True)

    def _pull_config(self) -> bool:
        """Pull Filebrowser config from router."""
        remote_settings = f"{self.remote_system_dir}/settings.json"
        local_settings = self.local_backup_dir / "settings.json"

        if self.conn.file_exists(remote_settings):
            return self.conn.download(remote_settings, local_settings)
        return False

    def _push_config(self) -> bool:
        """Push Filebrowser config to router."""
        local_settings = self.local_backup_dir / "settings.json"
        remote_settings = f"{self.remote_system_dir}/settings.json"

        if not local_settings.exists():
            return False

        if self.conn.upload(local_settings, remote_settings):
            self.conn.run("docker restart filebrowser", check=False)
            return True
        return False
