"""SSH connection management for router."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

console = Console()


class ConnectionError(Exception):
    """SSH connection error."""
    pass


class CommandError(Exception):
    """Command execution error."""
    pass


def get_ssh_password() -> str | None:
    """Get SSH password from environment or .env file."""
    # Try to load .env from repo root
    repo_root = Path(__file__).parent.parent.parent
    env_file = repo_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Check environment variable
    return os.environ.get("ROUTER_SSH_PASSWORD")


class SSHConnection:
    """SSH connection to router using sshpass + ssh."""

    def __init__(self, host: str, user: str = "root", password: str | None = None):
        self.host = host
        self.user = user
        # Password from parameter, environment, or .env file
        self.password = password or get_ssh_password()
        self._connected = False

    def _build_ssh_cmd(self, command: str, timeout: int = 30) -> list[str]:
        """Build SSH command with optional password."""
        # Common SSH options for older routers
        ssh_options = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-o", "HostKeyAlgorithms=+ssh-rsa",
            "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
        ]

        if self.password:
            return [
                "sshpass", "-p", self.password,
                "ssh", *ssh_options,
                f"{self.user}@{self.host}",
                command
            ]
        else:
            return [
                "ssh", *ssh_options,
                f"{self.user}@{self.host}",
                command
            ]

    def _build_scp_cmd(self, local: str, remote: str, upload: bool = True) -> list[str]:
        """Build SCP command with optional password."""
        ssh_options = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "HostKeyAlgorithms=+ssh-rsa",
            "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
        ]

        if self.password:
            base = ["sshpass", "-p", self.password, "scp", "-O", *ssh_options]
        else:
            base = ["scp", "-O", *ssh_options]

        if upload:
            return base + [local, f"{self.user}@{self.host}:{remote}"]
        else:
            return base + [f"{self.user}@{self.host}:{remote}", local]

    def test_connection(self) -> bool:
        """Test SSH connection to router."""
        try:
            result = self.run("echo 'connection_ok'", timeout=10)
            return "connection_ok" in result
        except Exception:
            return False

    def run(self, command: str, timeout: int = 30, check: bool = True) -> str:
        """Run command on router and return output."""
        cmd = self._build_ssh_cmd(command, timeout)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # SSH warnings go to stderr but don't mean failure
            if check and result.returncode != 0:
                stderr_lines = [
                    line for line in result.stderr.strip().split('\n')
                    if line and 'Warning: Permanently added' not in line
                ]
                error_msg = '\n'.join(stderr_lines) if stderr_lines else result.stdout.strip()
                if error_msg:
                    raise CommandError(f"Command failed: {command}\nError: {error_msg}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise CommandError(f"Command timed out after {timeout}s: {command}")
        except FileNotFoundError as e:
            if "sshpass" in str(e):
                raise ConnectionError(
                    "sshpass not found. Install with: brew install sshpass (macOS) "
                    "or apt install sshpass (Linux)"
                )
            raise

    def upload(self, local_path: str | Path, remote_path: str) -> bool:
        """Upload file to router."""
        local = str(local_path)
        cmd = self._build_scp_cmd(local, remote_path, upload=True)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                console.print(f"[red]Upload failed: {result.stderr}[/red]")
                return False
            return True
        except subprocess.TimeoutExpired:
            console.print("[red]Upload timed out[/red]")
            return False

    def upload_dir(self, local_dir: str | Path, remote_path: str) -> bool:
        """Upload directory recursively to router."""
        local = str(local_dir)
        cmd = self._build_scp_cmd(local, remote_path, upload=True)
        cmd.insert(-2 if self.password else -1, "-r")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                console.print(f"[red]Upload directory failed: {result.stderr}[/red]")
                return False
            return True
        except subprocess.TimeoutExpired:
            console.print("[red]Upload directory timed out[/red]")
            return False

    def download(self, remote_path: str, local_path: str | Path) -> bool:
        """Download file from router."""
        local = str(local_path)
        cmd = self._build_scp_cmd(local, remote_path, upload=False)

        Path(local).parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                console.print(f"[red]Download failed: {result.stderr}[/red]")
                return False
            return True
        except subprocess.TimeoutExpired:
            console.print("[red]Download timed out[/red]")
            return False

    def download_dir(self, remote_path: str, local_dir: str | Path) -> bool:
        """Download directory recursively from router."""
        local = str(local_dir)
        cmd = self._build_scp_cmd(local, remote_path, upload=False)
        cmd.insert(-2 if self.password else -1, "-r")

        Path(local).mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                console.print(f"[red]Download directory failed: {result.stderr}[/red]")
                return False
            return True
        except subprocess.TimeoutExpired:
            console.print("[red]Download directory timed out[/red]")
            return False

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists on router."""
        result = self.run(f"test -f {remote_path} && echo 'exists' || echo 'not_found'", check=False)
        return "exists" in result

    def dir_exists(self, remote_path: str) -> bool:
        """Check if directory exists on router."""
        result = self.run(f"test -d {remote_path} && echo 'exists' || echo 'not_found'", check=False)
        return "exists" in result

    def read_file(self, remote_path: str) -> str:
        """Read file content from router."""
        return self.run(f"cat {remote_path}")

    def write_file(self, remote_path: str, content: str, backup: bool = True) -> bool:
        """Write content to file on router with optional backup."""
        if backup and self.file_exists(remote_path):
            self.run(f"cp {remote_path} {remote_path}.bak")

        escaped_content = content.replace("'", "'\"'\"'")
        self.run(f"echo '{escaped_content}' > {remote_path}", check=False)
        return True

    def create_symlink(self, target: str, link_path: str, force: bool = True) -> bool:
        """Create symlink on router."""
        flag = "-sf" if force else "-s"
        self.run(f"ln {flag} {target} {link_path}", check=False)
        return True

    def mkdir(self, remote_path: str, parents: bool = True) -> bool:
        """Create directory on router."""
        flag = "-p" if parents else ""
        self.run(f"mkdir {flag} {remote_path}", check=False)
        return True
