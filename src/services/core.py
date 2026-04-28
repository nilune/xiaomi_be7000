"""Core system deployer."""

from __future__ import annotations

from services.base import ServiceDeployer


class CoreDeployer(ServiceDeployer):
    """Deployer for shared router bootstrap assets."""

    service_name = "core"
    system_subdir = "core"
    startup_script_name = "core.sh"
    startup_service_name = "Core"

    def _upload_files(self) -> None:
        """Upload shared system files to router."""
        self._upload_system_dir()
        self._upload_startup_script()

    def disable(self) -> None:
        """Stop the core service without deleting its files."""
        self.conn.run("/etc/init.d/core stop", check=False)
        self.conn.run("/etc/init.d/core disable", check=False)

    def preview_disable(self) -> list[str]:
        """Describe what disable() would do."""
        return ["/etc/init.d/core stop", "/etc/init.d/core disable"]
