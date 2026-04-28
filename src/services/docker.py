"""Shared helpers for Docker-based services."""

from __future__ import annotations

import base64
import hashlib
import os
import shlex
from collections.abc import Iterable

from services.base import ServiceDeployer


class DockerServiceDeployer(ServiceDeployer):
    """Base deployer for services that run as a single Docker container."""

    container_name: str = ""

    def should_run_from_startup(self) -> bool:
        """Docker containers use Docker restart policies instead of startup.sh."""
        return False

    def disable(self) -> None:
        """Stop and remove the container while keeping persistent data."""
        if not self.container_name:
            return
        docker_bin = shlex.quote(self.docker_bin)
        container_name = shlex.quote(self.container_name)
        self.conn.run(f"{docker_bin} stop {container_name}", check=False)
        self.conn.run(f"{docker_bin} rm {container_name}", check=False)

    def preview_disable(self) -> list[str]:
        """Describe what disable() would do."""
        if not self.container_name:
            return []
        return [
            f"{self.docker_bin} stop {self.container_name}",
            f"{self.docker_bin} rm {self.container_name}",
        ]

    @property
    def docker_bin(self) -> str:
        """Absolute path to the router Docker binary."""
        return f"{self.config.router_usb_dir}/mi_docker/docker-binaries/docker"

    def ensure_image_present(self, image: str) -> None:
        """Pull the image only when it is missing locally on the router."""
        docker_bin = shlex.quote(self.docker_bin)
        quoted_image = shlex.quote(image)
        inspect_cmd = f"{docker_bin} image inspect {quoted_image} >/dev/null 2>&1 && echo yes"
        exists = self.conn.run(inspect_cmd, check=False)
        if exists.strip() != "yes":
            self.conn.run(f"{docker_bin} pull {quoted_image}", check=True, timeout=300)

    @staticmethod
    def filebrowser_password_hash(password: str) -> str:
        """Create a bcrypt hash compatible with Filebrowser quick setup."""
        try:
            import bcrypt
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency 'bcrypt'. Run `uv sync` to install project deps."
            ) from exc

        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def shell_join(parts: Iterable[str]) -> str:
        """Safely quote a command for execution on the router."""
        return " ".join(shlex.quote(part) for part in parts)

    @staticmethod
    def make_password_fingerprint(value: str) -> str:
        """Stable fingerprint for change detection without storing the plain secret."""
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def env_assignment(name: str, value: str) -> str:
        """Render a Docker env-file assignment."""
        if "\n" in value:
            raise ValueError(f"Environment variable {name} must not contain newlines")
        return f"{name}={value}"

    @staticmethod
    def getenv(name: str, default: str | None = None) -> str:
        """Read an environment variable with an optional default."""
        value = os.environ.get(name)
        if value is None:
            return default or ""
        return value
