"""Service deployers for router services."""

from __future__ import annotations

from config import Config
from connection import SSHConnection
from services.adguard import AdGuardDeployer
from services.core import CoreDeployer
from services.filebrowser import FilebrowserDeployer
from services.v2raya import V2rayADeployer

SERVICE_DEPLOYERS = {
    "adguard": AdGuardDeployer,
    "core": CoreDeployer,
    "filebrowser": FilebrowserDeployer,
    "v2raya": V2rayADeployer,
}


def get_service_deployer(service_name: str, config: Config, conn: SSHConnection):
    """Instantiate a service deployer by name."""
    try:
        deployer_cls = SERVICE_DEPLOYERS[service_name]
    except KeyError as exc:
        known = ", ".join(sorted(SERVICE_DEPLOYERS))
        raise ValueError(f"Unknown service: {service_name}. Known services: {known}") from exc
    return deployer_cls(config, conn)
