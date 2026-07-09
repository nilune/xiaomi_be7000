"""Filebrowser service deployer."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import Any

from rich.console import Console

from services.docker import DockerServiceDeployer

console = Console()


class FilebrowserDeployer(DockerServiceDeployer):
    """Deployer for Filebrowser file manager."""

    service_name = "filebrowser"
    system_subdir = "filebrowser"
    container_name = "filebrowser"

    def get_service_config(self) -> dict[str, Any]:
        """Get filebrowser config from config.yml."""
        return self.config.get_service_config("filebrowser")

    @property
    def image_name(self) -> str:
        """Docker image pinned by config."""
        version = str(self.get_service_config().get("version", "latest")).strip() or "latest"
        return f"filebrowser/filebrowser:{version}"

    def _upload_files(self) -> None:
        """Upload Filebrowser files to router."""
        self._upload_system_dir()
        self._upload_generated_nginx_config()
        self._upload_generated_container_env()

    def _post_deploy(self) -> None:
        """Start or recreate the container after deploy."""
        self.ensure_image_present(self.image_name)
        self._prepare_runtime_dirs()
        self.disable()
        self.conn.run(self._render_docker_run_command(), check=True, timeout=300)
        # Validate and reload nginx to apply the proxy config
        if not self._validate_nginx_config():
            console.print("[yellow]Warning: nginx configuration validation failed[/yellow]")
        else:
            self._reload_nginx()

    def _upload_generated_nginx_config(self) -> None:
        """Generate and upload the nginx proxy config."""
        remote_nginx = f"{self.remote_system_dir}/etc/nginx/conf.d/filebrowser.conf"
        self.conn.mkdir(f"{self.remote_system_dir}/etc/nginx/conf.d", parents=True)
        self.conn.write_file(remote_nginx, self._render_nginx_config(), backup=False)

    def _upload_generated_container_env(self) -> None:
        """Generate and upload runtime env used by docker run."""
        remote_env = f"{self.remote_system_dir}/config/container.env"
        self.conn.mkdir(f"{self.remote_system_dir}/config", parents=True)
        self.conn.write_file(remote_env, self._render_container_env(), backup=False)

    def _render_container_env(self) -> str:
        """Render the environment file consumed by the startup script."""
        env_values = self._container_env_values()
        rendered = "\n".join(
            self.env_assignment(name, value) for name, value in sorted(env_values.items())
        )

        return (
            dedent(
                f"""\
                {rendered}
                """
            )
            .strip()
            + "\n"
        )

    def _render_nginx_config(self) -> str:
        """Render the nginx proxy config for filebrowser."""
        port = self.get_service_config().get("port", 8088)
        return dedent(
            f"""\
            server {{
                listen 80;
                server_name filebrowser filebrowser.lan;

                location / {{
                    proxy_pass http://127.0.0.1:{port}/;
                }}
            }}
            """
        )

    def extra_local_paths(self) -> list[Path]:
        """Additional files relevant for dry-run output."""
        return [
            self.config.init_dir / "_System" / "filebrowser" / "config" / "container.env.example",
        ]

    def preview_disable(self) -> list[str]:
        """Describe what disable() would do."""
        return super().preview_disable()

    def _render_docker_run_command(self) -> str:
        """Build a deterministic docker run command."""
        cfg = self.get_service_config()
        port = str(cfg.get("port", 8088))
        parts = [
            self.docker_bin,
            "run",
            "-d",
            "--name",
            self.container_name,
            "--user",
            "0:0",
            "--restart",
            "unless-stopped",
            "--env-file",
            f"{self.remote_system_dir}/config/container.env",
            "-p",
            f"{port}:{port}",
            "-v",
            f"{self.remote_system_dir}/config:/config",
            "-v",
            f"{self.remote_system_dir}/database:/database",
        ]

        for source in cfg.get("sources", []):
            path = str(source.get("path", "")).strip()
            if not path:
                continue
            parts.extend(["-v", f"{path}:{self._container_path(source.get('name', 'volume'))}"])

        parts.append(self.image_name)
        return self.shell_join(parts)

    def _container_env_values(self) -> dict[str, str]:
        """Build env vars consumed by Filebrowser inside the container."""
        cfg = self.get_service_config()
        port = str(cfg.get("port", 8088))
        username = str(cfg.get("initial_username", "admin"))
        password = str(cfg.get("initial_password", "admin"))
        hashed_password = self.filebrowser_password_hash(password)

        return {
            "FB_ADDRESS": "0.0.0.0",
            "FB_DATABASE": "/database/filebrowser.db",
            "FB_PASSWORD": hashed_password,
            "FB_PORT": port,
            "FB_ROOT": "/srv",
            "FB_USERNAME": username,
            "ROUTER_FILEBROWSER_IMAGE": self.image_name,
            "ROUTER_FILEBROWSER_PASSWORD_FINGERPRINT": self.make_password_fingerprint(password),
        }

    def _prepare_runtime_dirs(self) -> None:
        """Make bind-mounted directories writable for the container user."""
        config_dir = f"{self.remote_system_dir}/config"
        database_dir = f"{self.remote_system_dir}/database"
        self.conn.mkdir(config_dir, parents=True)
        self.conn.mkdir(database_dir, parents=True)
        self.conn.run(f"chown -R 1000:1000 {config_dir} {database_dir}", check=False)
        self.conn.run(f"chmod 775 {config_dir} {database_dir}", check=False)

    @staticmethod
    def _container_path(name: str) -> str:
        """Convert a source name into a stable container path."""
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        return f"/srv/{normalized}"
