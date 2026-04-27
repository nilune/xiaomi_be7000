"""Sync managed router files to and from the local repository."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path, PurePosixPath

from config import Config
from connection import SSHConnection

SYSTEM_CONFIGS = ("dhcp", "firewall", "network", "wireless")


class SyncManager:
    """Synchronize managed files between the router and ./sync."""

    def __init__(self, config: Config):
        self.config = config

    def available_targets(self) -> list[str]:
        """Return known sync target names."""
        return ["all", *SYSTEM_CONFIGS, "startup", "core", "adguard", "v2raya", "filebrowser"]

    def describe_target(self, target: str) -> list[str]:
        """Return remote paths for a target."""
        system_dir = self.config.system_dir
        mapping = {
            "dhcp": ["/etc/config/dhcp"],
            "firewall": ["/etc/config/firewall"],
            "network": ["/etc/config/network"],
            "wireless": ["/etc/config/wireless"],
            "startup": ["/data/startup.sh"],
            "core": [
                f"{system_dir}/core/etc",
                f"{system_dir}/core/usr/bin/core.sh",
                "/data/services/core.sh",
            ],
            "adguard": [
                f"{system_dir}/adGuardHome/etc",
                f"{system_dir}/adGuardHome/adguardhome.yaml",
                "/data/services/adguardhome.sh",
            ],
            "v2raya": [
                f"{system_dir}/v2raya/etc",
                "/data/services/v2raya.sh",
                "/data/scripts/update_geo_files.sh",
            ],
            "filebrowser": [
                f"{system_dir}/filebrowser/etc",
                f"{system_dir}/filebrowser/config",
                f"{system_dir}/filebrowser/database",
                "/data/services/filebrowser.sh",
            ],
        }

        if target == "all":
            ordered = OrderedDict()
            for item in ["startup", *SYSTEM_CONFIGS, "core", "adguard", "v2raya", "filebrowser"]:
                for path in mapping[item]:
                    ordered[path] = None
            return list(ordered.keys())

        if target not in mapping:
            raise ValueError(f"Unknown sync target: {target}")

        return mapping[target]

    def local_path_for_remote(self, remote_path: str) -> Path:
        """Map remote router path to local ./sync path."""
        remote = PurePosixPath(remote_path)
        system_root = PurePosixPath(self.config.system_dir)

        if str(remote).startswith(str(system_root)):
            relative = remote.relative_to(system_root)
            return self.config.sync_dir / "_System" / Path(str(relative))

        return self.config.sync_dir / Path(str(remote).lstrip("/"))

    def pull(self, conn: SSHConnection, target: str) -> list[tuple[str, bool]]:
        """Pull a target from the router into ./sync."""
        results = []
        for remote_path in self.describe_target(target):
            local_path = self.local_path_for_remote(remote_path)
            success = self._pull_single(conn, remote_path, local_path)
            results.append((remote_path, success))
        return results

    def push(self, conn: SSHConnection, target: str, dry_run: bool = False) -> list[tuple[str, bool]]:
        """Push a target from ./sync back to the router."""
        results = []
        for remote_path in self.describe_target(target):
            local_path = self.local_path_for_remote(remote_path)
            success = self._push_single(conn, local_path, remote_path, dry_run=dry_run)
            results.append((remote_path, success))
        return results

    def _pull_single(self, conn: SSHConnection, remote_path: str, local_path: Path) -> bool:
        """Pull one file or directory from the router."""
        if conn.dir_exists(remote_path):
            return conn.download_dir_exact(remote_path, local_path)
        if conn.file_exists(remote_path):
            return conn.download(remote_path, local_path)
        return False

    def _push_single(
        self,
        conn: SSHConnection,
        local_path: Path,
        remote_path: str,
        *,
        dry_run: bool = False,
    ) -> bool:
        """Push one local file or directory to the router."""
        if not local_path.exists():
            return False

        if dry_run:
            return True

        remote_parent = str(PurePosixPath(remote_path).parent)
        conn.mkdir(remote_parent, parents=True)

        if local_path.is_dir():
            return conn.upload_dir_exact(local_path, remote_path)
        return conn.upload(local_path, remote_path)
