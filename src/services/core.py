"""Core system deployer."""

from __future__ import annotations

from .base import ServiceDeployer


class CoreDeployer(ServiceDeployer):
    """Deployer for shared router bootstrap assets."""

    service_name = "core"
    system_subdir = "core"
    startup_script_name = "core.sh"

    def _upload_files(self) -> None:
        """Upload shared system files to router."""
        self._upload_system_dir()
        self._upload_startup_script()
