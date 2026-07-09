"""CLI interface for router deployer."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from config import Config, get_config
from connection import SSHConnection
from services import SERVICE_DEPLOYERS, get_service_deployer
from sync import SyncManager
from uci.dhcp import DHCPHandler

console = Console()
SERVICE_ALIASES = {"base": "startup"}


def require_config() -> Config:
    """Load configuration or terminate with a readable error."""
    return get_config()


def require_connection(config: Config) -> SSHConnection:
    """Create SSH connection to router."""
    conn = SSHConnection(config.router_address, config.router_user)

    if not conn.test_connection():
        console.print(f"[red]Cannot connect to router at {config.router_address}[/red]")
        console.print("Check SSH access and ROUTER_SSH_PASSWORD.")
        raise SystemExit(1)

    return conn


@click.group()
@click.version_option(version="0.1.0")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Manage Xiaomi BE7000 router bootstrap, sync, and DHCP state."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.group("config")
def config_cmd() -> None:
    """Show and validate local configuration."""


@config_cmd.command("show")
def show_config() -> None:
    """Show the active config.yml values."""
    config = require_config()

    table = Table(show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Address", config.router_address)
    table.add_row("User", config.router_user)
    table.add_row("USB Dir", config.router_usb_dir)
    table.add_row("Init Dir", str(config.init_dir))
    table.add_row("Sync Dir", str(config.sync_dir))

    console.print(table)
    console.print("\n[blue]Enabled Services[/blue]")
    for name, cfg in config.services.items():
        console.print(f"  - {name}: {'enabled' if cfg.get('enabled') else 'disabled'}")


@config_cmd.command("validate")
def validate_config() -> None:
    """Validate config.yml and test SSH connection."""
    config = require_config()
    issues = config.validate()
    if issues:
        console.print("[red]Configuration issues:[/red]")
        for issue in issues:
            console.print(f"  - {issue}")
        raise SystemExit(1)

    require_connection(config)
    console.print(f"[green]Configuration is valid. Router: {config.router_address}[/green]")


@main.group()
def dhcp() -> None:
    """Inspect and edit static hosts in /etc/config/dhcp."""


@dhcp.command("leases")
def leases_cmd() -> None:
    """Show current DHCP leases from /tmp/dhcp.leases."""
    config = require_config()
    conn = require_connection(config)

    try:
        leases_raw = conn.read_file("/tmp/dhcp.leases")
    except Exception as exc:
        console.print(f"[red]Failed to read DHCP leases: {exc}[/red]")
        raise SystemExit(1) from exc

    table = Table(title="DHCP Leases")
    table.add_column("MAC", style="cyan")
    table.add_column("IP", style="green")
    table.add_column("Hostname", style="yellow")
    table.add_column("Lease", style="dim")

    for line in leases_raw.strip().splitlines():
        parts = line.split()
        if len(parts) >= 4:
            table.add_row(parts[1], parts[2], parts[3], parts[0])

    console.print(table)


@dhcp.command("hosts")
def dhcp_hosts() -> None:
    """Show static host entries from /etc/config/dhcp."""
    config = require_config()
    conn = require_connection(config)
    handler = DHCPHandler(config)
    hosts = handler.list_static_hosts(conn)

    if not hosts:
        console.print("[yellow]No static hosts found.[/yellow]")
        return

    table = Table(title="Static DHCP Hosts")
    table.add_column("Section", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("MAC", style="green")
    table.add_column("IP", style="yellow")

    for host in hosts:
        table.add_row(host["section"], host["name"], host["mac"], host["ip"])

    console.print(table)


@dhcp.command("candidates")
def dhcp_candidates() -> None:
    """Show lease entries that are not yet pinned as static hosts."""
    config = require_config()
    conn = require_connection(config)
    handler = DHCPHandler(config)
    candidates = handler.list_static_candidates(conn)

    if not candidates:
        console.print("[yellow]No static-IP candidates found.[/yellow]")
        return

    table = Table(title="Static IP Candidates")
    table.add_column("MAC", style="cyan")
    table.add_column("IP", style="green")
    table.add_column("Hostname", style="yellow")
    table.add_column("Reason", style="dim")

    for host in candidates:
        table.add_row(host["mac"], host["ip"], host["name"], host["reason"])

    console.print(table)


@dhcp.command("add")
@click.argument("name")
@click.argument("mac")
@click.argument("ip")
@click.option("--replace", is_flag=True, help="Replace conflicting entries by name, MAC, or IP.")
@click.option("--restart", is_flag=True, help="Restart dnsmasq after commit.")
def dhcp_add(name: str, mac: str, ip: str, replace: bool, restart: bool) -> None:
    """Add a static DHCP host."""
    config = require_config()
    conn = require_connection(config)
    handler = DHCPHandler(config)

    result = handler.add_static_host(
        conn,
        name=name,
        mac=mac,
        ip=ip,
        replace=replace,
        restart_dnsmasq=restart,
    )

    if not result["added"]:
        console.print("[red]Conflicting static hosts already exist:[/red]")
        for host in result["conflicts"]:
            console.print(f"  - {host['name']} ({host['mac']} -> {host['ip']}) [{host['section']}]")
        console.print("[yellow]Use --replace to overwrite conflicting entries.[/yellow]")
        raise SystemExit(1)

    if result["replaced"]:
        console.print(f"[yellow]Replaced: {', '.join(result['replaced'])}[/yellow]")
    console.print(f"[green]Added static host '{name}' in section '{result['section']}'.[/green]")
    if restart:
        console.print("[green]dnsmasq restarted.[/green]")


@dhcp.command("remove")
@click.argument("value")
@click.option(
    "--by",
    type=click.Choice(["any", "name", "ip", "mac", "section"], case_sensitive=False),
    default="any",
    show_default=True,
    help="Field used to match the host entry.",
)
@click.option("--restart", is_flag=True, help="Restart dnsmasq after commit.")
def dhcp_remove(value: str, by: str, restart: bool) -> None:
    """Remove static DHCP hosts by name, IP, MAC, or section."""
    config = require_config()
    conn = require_connection(config)
    handler = DHCPHandler(config)
    result = handler.remove_static_host(conn, value=value, by=by, restart_dnsmasq=restart)

    if not result["removed"]:
        console.print("[yellow]No matching static hosts found.[/yellow]")
        raise SystemExit(1)

    for host in result["removed"]:
        console.print(f"[green]Removed[/green] {host['name']} ({host['mac']} -> {host['ip']})")
    if restart:
        console.print("[green]dnsmasq restarted.[/green]")


@main.group()
def sync() -> None:
    """Pull or push managed router files via ./sync."""


@sync.command("pull")
@click.argument("target", required=False, default="all")
@click.option("--all", "pull_all", is_flag=True, help="Alias for pulling all managed targets.")
def pull_cmd(target: str, pull_all: bool) -> None:
    """Pull managed files from the router into ./sync."""
    config = require_config()
    conn = require_connection(config)
    manager = SyncManager(config)
    target_name = "all" if pull_all else target

    try:
        results = manager.pull(conn, target_name)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc

    _print_sync_results(manager, results)


@sync.command("push")
@click.argument("target")
@click.option("--dry-run", is_flag=True, help="Show which sync paths would be uploaded.")
def push_cmd(target: str, dry_run: bool) -> None:
    """Push managed files from ./sync back to the router."""
    config = require_config()
    manager = SyncManager(config)

    try:
        remote_paths = manager.describe_target(target)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc

    if dry_run:
        for remote_path in remote_paths:
            local_path = _display_repo_relative_path(
                manager.config.repo_root,
                manager.local_path_for_remote(remote_path),
            )
            console.print(f"{local_path} -> {remote_path}")
        return

    conn = require_connection(config)
    results = manager.push(conn, target)
    _print_sync_results(manager, results, reverse=True)


@main.group()
def deploy() -> None:
    """Deploy initial service assets from ./init."""


@deploy.command("run")
@click.argument("service", required=False)
@click.option("--dry-run", is_flag=True, help="Show what would be uploaded.")
def deploy_run(service: str | None, dry_run: bool) -> None:
    """Deploy one enabled service or all enabled services."""
    config = require_config()
    if service:
        requested_service = SERVICE_ALIASES.get(service, service)
        if requested_service not in SERVICE_DEPLOYERS:
            known = ", ".join(sorted(SERVICE_DEPLOYERS))
            console.print(f"[red]Unknown service: {requested_service}[/red]")
            console.print(f"[yellow]Known services: {known}[/yellow]")
            raise SystemExit(1)

        conn = require_connection(config) if not dry_run else SSHConnection(
            config.router_address,
            config.router_user,
        )
        _deploy_one_service(requested_service, config, conn, dry_run=dry_run)
        return

    conn = require_connection(config) if not dry_run else SSHConnection(
        config.router_address,
        config.router_user,
    )

    _deploy_one_service("startup", config, conn, dry_run=dry_run)

    enabled_services = [name for name, cfg in config.services.items() if cfg.get("enabled", False)]
    disabled_services = [
        name for name in SERVICE_DEPLOYERS if name not in {"startup", *enabled_services}
    ]

    if not enabled_services and not disabled_services:
        console.print("[yellow]No managed services found in config.yml.[/yellow]")
        return

    for svc in enabled_services:
        _deploy_one_service(svc, config, conn, dry_run=dry_run)

    for svc in disabled_services:
        _disable_one_service(svc, config, conn, dry_run=dry_run)


@main.group()
def utils() -> None:
    """Run low-level helper commands."""


@utils.command("exec")
@click.argument("command", metavar="COMMAND")
@click.option("--show-stderr", is_flag=True, help="Print stderr from the SSH command.")
def exec_cmd(command: str, show_stderr: bool) -> None:
    """Execute a shell command on the router."""
    config = require_config()
    conn = require_connection(config)

    result = conn.run(command, check=False)
    if result:
        console.print(result)

    if show_stderr:
        cmd = conn._build_ssh_cmd(command, 30)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.stderr:
            console.print(proc.stderr.strip())


def _deploy_one_service(
    service_name: str,
    config: Config,
    conn: SSHConnection,
    *,
    dry_run: bool,
) -> None:
    """Deploy one service with consistent output."""
    if dry_run:
        console.print(f"\n[yellow]{service_name}[/yellow]")
    else:
        console.print(f"\n[blue]Deploying {service_name}...[/blue]")

    try:
        deployer = get_service_deployer(service_name, config, conn)
        deployer.deploy(dry_run=dry_run)
        if not dry_run:
            console.print(f"[green]✓ Deployed {service_name}[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to deploy {service_name}: {exc}[/red]")
        raise SystemExit(1) from exc


def _disable_one_service(
    service_name: str,
    config: Config,
    conn: SSHConnection,
    *,
    dry_run: bool,
) -> None:
    """Disable one service without deleting its data."""
    deployer = get_service_deployer(service_name, config, conn)
    if dry_run:
        console.print(f"\n[dim]{service_name} (disabled in config.yml)[/dim]")
        for action in deployer.preview_disable():
            console.print(f"  [dim]- {action}[/dim]")
        return

    console.print(f"\n[blue]Disabling {service_name}...[/blue]")
    try:
        deployer.disable()
        console.print(f"[green]✓ Disabled {service_name}[/green]")
    except Exception as exc:
        console.print(f"[red]Failed to disable {service_name}: {exc}[/red]")
        raise SystemExit(1) from exc


def _print_sync_results(
    manager: SyncManager,
    results: Iterable[tuple[str, bool]],
    *,
    reverse: bool = False,
) -> None:
    """Render sync pull/push results consistently."""
    for remote_path, success in results:
        status = "[green]✓[/green]" if success else "[yellow]-[/yellow]"
        local_path = _display_repo_relative_path(
            manager.config.repo_root,
            manager.local_path_for_remote(remote_path),
        )
        if reverse:
            console.print(f"{status} {local_path} -> {remote_path}")
        else:
            console.print(f"{status} {remote_path} -> {local_path}")


def _display_repo_relative_path(repo_root: Path, path: Path) -> Path | str:
    """Render a path relative to the repository root when possible."""
    try:
        return path.relative_to(repo_root)
    except ValueError:
        return path


if __name__ == "__main__":
    main()
