"""Filebrowser service deployer (Docker-based)."""

from __future__ import annotations

from typing import Any

from .base import ServiceDeployer


class FilebrowserDeployer(ServiceDeployer):
    """Deployer for Filebrowser file manager (Docker)."""

    service_name = "filebrowser"
    system_subdir = ""
    startup_script_name = None

    def get_service_config(self) -> dict[str, Any]:
        """Get filebrowser config from config.yml."""
        return self.config.get_service_config("filebrowser")

    def _upload_files(self) -> None:
        """Filebrowser has no init assets in the repository."""

    def _post_deploy(self) -> None:
        """Start Filebrowser container."""
        self._start_container()

    def _start_container(self) -> None:
        """Start filebrowser Docker container."""
        cfg = self.get_service_config()
        port = cfg.get("port", 8088)
        sources = cfg.get("sources", [])

        self.conn.run("docker stop filebrowser 2>/dev/null || true", check=False)
        self.conn.run("docker rm filebrowser 2>/dev/null || true", check=False)

        volumes = []
        for source in sources:
            path = source.get("path", "")
            name = source.get("name", "volume")
            if path:
                container_path = f"/srv/{name.lower().replace(' ', '_').replace('-', '_')}"
                volumes.append(f"-v {path}:{container_path}")

        volumes_str = " ".join(volumes)
        cmd = (
            f"docker run -d --name filebrowser -p {port}:80 {volumes_str} "
            f"--restart unless-stopped filebrowser/filebrowser:latest"
        ).strip()
        self.conn.run(cmd, check=True)
