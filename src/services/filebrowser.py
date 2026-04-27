"""Filebrowser service deployer."""

from __future__ import annotations

import shlex
from pathlib import Path
from textwrap import dedent
from typing import Any

from services.base import ServiceDeployer


class FilebrowserDeployer(ServiceDeployer):
    """Deployer for Filebrowser file manager."""

    service_name = "filebrowser"
    system_subdir = "filebrowser"
    startup_script_name = "filebrowser.sh"
    image_name = "filebrowser/filebrowser:latest"

    def get_service_config(self) -> dict[str, Any]:
        """Get filebrowser config from config.yml."""
        return self.config.get_service_config("filebrowser")

    def _upload_files(self) -> None:
        """Upload Filebrowser files to router."""
        self._upload_system_dir()
        self._upload_generated_nginx_config()
        self._upload_generated_startup_script()
        self._upload_generated_container_env()

    def _post_deploy(self) -> None:
        """Start Filebrowser after deploy."""
        if self.remote_startup_script:
            self.conn.run(self.remote_startup_script, check=True)

    def _upload_generated_startup_script(self) -> None:
        """Generate and upload the startup script."""
        if not self.remote_startup_script:
            return

        script = self._render_startup_script()
        self.conn.mkdir("/data/services", parents=True)
        self.conn.write_file(self.remote_startup_script, script, backup=False)
        self.conn.run(f"chmod +x {self.remote_startup_script}", check=False)

    def _upload_generated_nginx_config(self) -> None:
        """Generate and upload the nginx proxy config."""
        remote_nginx = f"{self.remote_system_dir}/etc/nginx/conf.d/filebrowser.conf"
        self.conn.mkdir(f"{self.remote_system_dir}/etc/nginx/conf.d", parents=True)
        self.conn.write_file(remote_nginx, self._render_nginx_config(), backup=False)

    def _upload_generated_container_env(self) -> None:
        """Generate and upload runtime env used by the startup script."""
        remote_env = f"{self.remote_system_dir}/config/container.env"
        self.conn.mkdir(f"{self.remote_system_dir}/config", parents=True)
        self.conn.write_file(remote_env, self._render_container_env(), backup=False)

    def _render_startup_script(self) -> str:
        """Render a deterministic startup script for the router."""
        return (
            dedent(
            """\
            #!/bin/sh

            FILEBROWSER_DIR="${SYSTEM_DIR}/filebrowser"
            FILEBROWSER_CONFIG_DIR="${FILEBROWSER_DIR}/config"
            FILEBROWSER_DATABASE_DIR="${FILEBROWSER_DIR}/database"
            FILEBROWSER_LOG_DIR="${FILEBROWSER_DIR}/log"
            FILEBROWSER_NGINX_CONF="${FILEBROWSER_DIR}/etc/nginx/conf.d/filebrowser.conf"
            FILEBROWSER_ENV_FILE="${FILEBROWSER_CONFIG_DIR}/container.env"

            mkdir -p "${FILEBROWSER_CONFIG_DIR}" "${FILEBROWSER_DATABASE_DIR}" "${FILEBROWSER_LOG_DIR}"
            touch "${FILEBROWSER_CONFIG_DIR}/settings.json"

            exec >> "${FILEBROWSER_LOG_DIR}/startup.log" 2>&1
            echo "===== $(date '+%F %T') filebrowser startup started ====="

            if [ -f "${FILEBROWSER_ENV_FILE}" ]; then
                . "${FILEBROWSER_ENV_FILE}"
            fi

            FILEBROWSER_PORT="${FILEBROWSER_PORT:-8088}"
            FILEBROWSER_INITIAL_USERNAME="${FILEBROWSER_INITIAL_USERNAME:-admin}"
            FILEBROWSER_INITIAL_PASSWORD="${FILEBROWSER_INITIAL_PASSWORD:-admin}"
            FILEBROWSER_IMAGE="${FILEBROWSER_IMAGE:-filebrowser/filebrowser:latest}"
            FILEBROWSER_ROOT="${FILEBROWSER_ROOT:-/srv}"

            DOCKER_BIN="${USB_DIR}/mi_docker/docker-binaries/docker"
            if [ ! -x "${DOCKER_BIN}" ]; then
                DOCKER_BIN="docker"
            fi

            ln -sfn "${FILEBROWSER_NGINX_CONF}" /etc/nginx/conf.d/filebrowser.conf
            echo "Linked /etc/nginx/conf.d/filebrowser.conf -> ${FILEBROWSER_NGINX_CONF}"

            PASSWORD_HASH=""
            if [ ! -f "${FILEBROWSER_DATABASE_DIR}/filebrowser.db" ]; then
                PASSWORD_HASH=$("${DOCKER_BIN}" run --rm "${FILEBROWSER_IMAGE}" hash "${FILEBROWSER_INITIAL_PASSWORD}")
                echo "Initialized filebrowser password hash for first boot"
            fi

            "${DOCKER_BIN}" stop filebrowser 2>/dev/null || true
            "${DOCKER_BIN}" rm filebrowser 2>/dev/null || true

            set -- run -d --name filebrowser \
                -p "${FILEBROWSER_PORT}:80" \
                -v "${FILEBROWSER_DATABASE_DIR}:/database" \
                -v "${FILEBROWSER_CONFIG_DIR}:/config"

            if [ -n "${FILEBROWSER_MOUNTS}" ]; then
                while IFS= read -r mount_pair; do
                    [ -n "${mount_pair}" ] || continue
                    set -- "$@" -v "${mount_pair}"
                done <<EOF
            ${FILEBROWSER_MOUNTS}
            EOF
            fi

            set -- "$@" \
                --restart unless-stopped \
                "${FILEBROWSER_IMAGE}" \
                --address 0.0.0.0 \
                --port 80 \
                --root "${FILEBROWSER_ROOT}" \
                --database /database/filebrowser.db \
                --config /config/settings.json

            if [ -n "${PASSWORD_HASH}" ]; then
                set -- "$@" --username "${FILEBROWSER_INITIAL_USERNAME}" --password "${PASSWORD_HASH}"
            fi

            set -x
            "${DOCKER_BIN}" "$@"
            set +x
            """
        )
            .strip()
            + "\n"
        )

    def _render_container_env(self) -> str:
        """Render the environment file consumed by the startup script."""
        cfg = self.get_service_config()
        port = cfg.get("port", 8088)
        username = cfg.get("initial_username", "admin")
        password = cfg.get("initial_password", "admin")
        sources = cfg.get("sources", [])

        mount_lines = [f"{source['path']}:{self._container_path(source.get('name', 'volume'))}" for source in sources if source.get("path")]
        mounts = "\n".join(mount_lines)

        return (
            dedent(
            f"""\
            FILEBROWSER_PORT={shlex.quote(str(port))}
            FILEBROWSER_INITIAL_USERNAME={shlex.quote(str(username))}
            FILEBROWSER_INITIAL_PASSWORD={shlex.quote(str(password))}
            FILEBROWSER_IMAGE={shlex.quote(self.image_name)}
            FILEBROWSER_ROOT=/srv
            FILEBROWSER_MOUNTS='{mounts}'
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
            self.config.init_dir / "data" / "services" / "filebrowser.sh",
            self.config.init_dir / "_System" / "filebrowser" / "config" / "settings.json",
            self.config.init_dir / "_System" / "filebrowser" / "config" / "container.env.example",
        ]

    @staticmethod
    def _container_path(name: str) -> str:
        """Convert a source name into a stable container path."""
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        return f"/srv/{normalized}"
