"""SSH connection management for router."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path, PurePosixPath

from dotenv import load_dotenv
from rich.console import Console

console = Console()


class ConnectionError(Exception):
    """SSH connection error."""


class CommandError(Exception):
    """Command execution error."""


def get_ssh_password() -> str | None:
    """Get SSH password from environment or .env file."""
    repo_root = Path(__file__).resolve().parent.parent
    env_file = repo_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    return os.environ.get("ROUTER_SSH_PASSWORD")


class SSHConnection:
    """SSH connection to router using sshpass + ssh."""

    def __init__(self, host: str, user: str = "root", password: str | None = None):
        self.host = host
        self.user = user
        self.password = password or get_ssh_password()

    def _build_ssh_cmd(self, command: str, timeout: int = 30) -> list[str]:
        """Build SSH command with optional password."""
        ssh_options = [
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "HostKeyAlgorithms=+ssh-rsa",
            "-o",
            "PubkeyAcceptedAlgorithms=+ssh-rsa",
        ]

        if self.password:
            return [
                "sshpass",
                "-p",
                self.password,
                "ssh",
                *ssh_options,
                f"{self.user}@{self.host}",
                command,
            ]
        return ["ssh", *ssh_options, f"{self.user}@{self.host}", command]

    def _build_scp_cmd(self, local: str, remote: str, upload: bool = True) -> list[str]:
        """Build SCP command with optional password."""
        ssh_options = [
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "HostKeyAlgorithms=+ssh-rsa",
            "-o",
            "PubkeyAcceptedAlgorithms=+ssh-rsa",
        ]

        if self.password:
            base = ["sshpass", "-p", self.password, "scp", "-O", *ssh_options]
        else:
            base = ["scp", "-O", *ssh_options]

        if upload:
            return base + [local, f"{self.user}@{self.host}:{remote}"]
        return base + [f"{self.user}@{self.host}:{remote}", local]

    def test_connection(self) -> bool:
        """Test SSH connection to router."""
        try:
            return "connection_ok" in self.run("echo 'connection_ok'", timeout=10)
        except Exception:
            return False

    def run(self, command: str, timeout: int = 30, check: bool = True) -> str:
        """Run command on router and return stdout."""
        cmd = self._build_ssh_cmd(command, timeout)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise CommandError(f"Command timed out after {timeout}s: {command}") from None
        except FileNotFoundError as e:
            if "sshpass" in str(e):
                raise ConnectionError(
                    "sshpass not found. Install with: brew install hudochenkov/sshpass/sshpass "
                    "or apt install sshpass"
                ) from None
            raise

        if check and result.returncode != 0:
            stderr_lines = [
                line
                for line in result.stderr.strip().split("\n")
                if line and "Warning: Permanently added" not in line
            ]
            error_msg = "\n".join(stderr_lines) if stderr_lines else result.stdout.strip()
            raise CommandError(f"Command failed: {command}\nError: {error_msg}")

        return result.stdout.strip()

    def upload(self, local_path: str | Path, remote_path: str) -> bool:
        """Upload file to router."""
        cmd = self._build_scp_cmd(str(local_path), remote_path, upload=True)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            console.print("[red]Upload timed out[/red]")
            return False

        if result.returncode != 0:
            console.print(f"[red]Upload failed: {result.stderr}[/red]")
            return False
        return True

    def upload_dir(self, local_dir: str | Path, remote_path: str) -> bool:
        """Upload directory recursively to router."""
        cmd = self._build_scp_cmd(str(local_dir), remote_path, upload=True)
        cmd.insert(-2 if self.password else -1, "-r")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            console.print("[red]Upload directory timed out[/red]")
            return False

        if result.returncode != 0:
            console.print(f"[red]Upload directory failed: {result.stderr}[/red]")
            return False
        return True

    def upload_dir_exact(self, local_dir: str | Path, remote_dir: str) -> bool:
        """Upload directory to an exact remote directory path."""
        remote_parent = str(PurePosixPath(remote_dir).parent)
        self.mkdir(remote_parent, parents=True)
        return self.upload_dir(local_dir, remote_parent)

    def download(self, remote_path: str, local_path: str | Path) -> bool:
        """Download file from router."""
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        cmd = self._build_scp_cmd(str(local), remote_path, upload=False)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            console.print("[red]Download timed out[/red]")
            return False

        if result.returncode != 0:
            console.print(f"[red]Download failed: {result.stderr}[/red]")
            return False
        return True

    def download_dir(self, remote_path: str, local_dir: str | Path) -> bool:
        """Download directory recursively from router."""
        local = Path(local_dir)
        local.mkdir(parents=True, exist_ok=True)
        cmd = self._build_scp_cmd(str(local), remote_path, upload=False)
        cmd.insert(-2 if self.password else -1, "-r")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            console.print("[red]Download directory timed out[/red]")
            return False

        if result.returncode != 0:
            console.print(f"[red]Download directory failed: {result.stderr}[/red]")
            return False
        return True

    def download_dir_exact(self, remote_dir: str, local_dir: str | Path) -> bool:
        """Download directory to an exact local directory path."""
        local = Path(local_dir)
        local.parent.mkdir(parents=True, exist_ok=True)
        return self.download_dir(remote_dir, local.parent)

    def path_exists(self, remote_path: str) -> bool:
        """Check if path exists on router."""
        path = shlex.quote(remote_path)
        result = self.run(f"test -e {path} && echo 'exists' || echo 'not_found'", check=False)
        return "exists" in result

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists on router."""
        path = shlex.quote(remote_path)
        result = self.run(f"test -f {path} && echo 'exists' || echo 'not_found'", check=False)
        return "exists" in result

    def dir_exists(self, remote_path: str) -> bool:
        """Check if directory exists on router."""
        path = shlex.quote(remote_path)
        result = self.run(f"test -d {path} && echo 'exists' || echo 'not_found'", check=False)
        return "exists" in result

    def read_file(self, remote_path: str) -> str:
        """Read file content from router."""
        return self.run(f"cat {shlex.quote(remote_path)}")

    def write_file(self, remote_path: str, content: str, backup: bool = True) -> bool:
        """Write content to file on router with optional backup."""
        quoted_path = shlex.quote(remote_path)
        if backup and self.path_exists(remote_path):
            self.run(f"cp {quoted_path} {quoted_path}.bak")

        escaped_content = content.replace("'", "'\"'\"'")
        self.run(f"printf '%s' '{escaped_content}' > {quoted_path}", check=True)
        return True

    def create_symlink(self, target: str, link_path: str, force: bool = True) -> bool:
        """Create symlink on router."""
        flag = "-sf" if force else "-s"
        self.run(f"ln {flag} {shlex.quote(target)} {shlex.quote(link_path)}", check=False)
        return True

    def mkdir(self, remote_path: str, parents: bool = True) -> bool:
        """Create directory on router."""
        flag = "-p " if parents else ""
        self.run(f"mkdir {flag}{shlex.quote(remote_path)}", check=False)
        return True

    def remove_file(self, remote_path: str) -> bool:
        """Remove a file on router if it exists."""
        self.run(f"rm -f {shlex.quote(remote_path)}", check=False)
        return True
