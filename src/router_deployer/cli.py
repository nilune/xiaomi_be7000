"""CLI interface for router deployer."""

from __future__ import annotations

from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .config import Config, get_config, reload_config
from .connection import SSHConnection

console = Console()


def require_config() -> Config:
    """Get or load configuration."""
    return get_config()


def require_connection(config: Config) -> SSHConnection:
    """Create SSH connection to router."""
    conn = SSHConnection(config.router_address, config.router_user)

    if not conn.test_connection():
        console.print(f"[red]Cannot connect to router at {config.router_address}[/red]")
        console.print("\nCheck that:")
        console.print("  - Router is powered on and accessible")
        console.print("  - SSH is enabled on the router")
        console.print("  - ROUTER_SSH_PASSWORD is set (or in .env file)")
        raise SystemExit(1)

    return conn


# =====================
# Main CLI
# =====================

@click.group()
@click.version_option(version="0.1.0")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Router deployment and configuration management tool."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


# =====================
# Config commands
# =====================

@main.group("config")
def config_cmd() -> None:
    """Configuration management."""
    pass


@config_cmd.command("show")
@click.pass_context
def show_config(ctx: click.Context) -> None:
    """Show current configuration."""
    config = require_config()

    console.print("[blue]Router Configuration[/blue]\n")

    table = Table(show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Address", config.router_address)
    table.add_row("User", config.router_user)
    table.add_row("USB Dir", config.router_usb_dir)
    table.add_row("System Dir", config.system_dir)

    console.print(table)

    console.print("\n[blue]Enabled Services[/blue]")
    for name, cfg in config.services.items():
        if cfg.get("enabled"):
            console.print(f"  - {name}: {cfg.get('description', '')}")


@config_cmd.command("validate")
@click.pass_context
def validate_config(ctx: click.Context) -> None:
    """Validate configuration and test connection."""
    config = require_config()

    issues = config.validate()
    if issues:
        console.print("[red]Configuration issues:[/red]")
        for issue in issues:
            console.print(f"  - {issue}")
        return

    console.print("[green]Configuration is valid[/green]")

    conn = require_connection(config)
    console.print(f"[green]Connected to router at {config.router_address}[/green]")


# =====================
# DHCP commands
# =====================

@main.group()
def dhcp() -> None:
    """DHCP and static IP management."""
    pass


@dhcp.command("leases")
@click.pass_context
def leases_cmd(ctx: click.Context) -> None:
    """Show current DHCP leases from router."""
    config = require_config()
    conn = require_connection(config)

    try:
        leases_raw = conn.read_file("/tmp/dhcp.leases")

        table = Table(title="DHCP Leases")
        table.add_column("MAC Address", style="cyan")
        table.add_column("IP Address", style="green")
        table.add_column("Hostname", style="yellow")
        table.add_column("Lease Expiry", style="dim")

        for line in leases_raw.strip().split("\n"):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 4:
                table.add_row(parts[1], parts[2], parts[3], parts[0])

        console.print(table)

    except Exception as e:
        console.print(f"[red]Failed to read DHCP leases: {e}[/red]")


@dhcp.command("static")
@click.option("--preview", is_flag=True, help="Preview changes")
@click.option("--apply", "apply_changes", is_flag=True, help="Apply changes to router")
@click.option("--generate", is_flag=True, help="Generate config from hosts.yml")
@click.pass_context
def static_cmd(ctx: click.Context, preview: bool, apply_changes: bool, generate: bool) -> None:
    """Manage static DHCP entries.

    Examples:
        router dhcp static --preview    # Show what would change
        router dhcp static --apply      # Apply changes to router
        router dhcp static --generate   # Show generated entries
    """
    config = require_config()
    from .uci.dhcp import DHCPHandler

    handler = DHCPHandler(config)

    # Default: show preview
    if not generate and not apply_changes and not preview:
        preview = True

    if preview or apply_changes:
        conn = require_connection(config)
        changes = handler.preview_changes(conn)

        console.print("\n[bold]DHCP Static Entries Preview[/bold]\n")

        if changes["to_add"]:
            console.print(f"[green]Will ADD ({len(changes['to_add'])}):[/green]")
            for h in changes["to_add"]:
                console.print(f"  + {h['name']}: {h['mac']} -> {h['ip']}")

        if changes["to_update"]:
            console.print(f"[yellow]Will UPDATE ({len(changes['to_update'])}):[/yellow]")
            for h in changes["to_update"]:
                console.print(f"  ~ {h['name']}:")
                console.print(f"      old: {h['old'].get('mac')} -> {h['old'].get('ip')}")
                console.print(f"      new: {h['new'].get('mac')} -> {h['new'].get('ip')}")

        if changes["unchanged"]:
            console.print(f"[dim]Unchanged ({len(changes['unchanged'])}): {', '.join(changes['unchanged'])}[/dim]")

        if not changes["to_add"] and not changes["to_update"]:
            console.print("[green]No changes needed - inventory matches router[/green]")
            return

        if apply_changes:
            console.print("\n[yellow]Applying changes...[/yellow]")
            result = handler.apply_changes(conn, dry_run=False)

            if result.get("added"):
                console.print(f"[green]✓ Added: {', '.join(result['added'])}[/green]")
            if result.get("updated"):
                console.print(f"[green]✓ Updated: {', '.join(result['updated'])}[/green]")
            if result.get("failed"):
                console.print(f"[red]✗ Failed: {result['failed']}[/red]")

            console.print("\n[yellow]Run 'service dnsmasq restart' on router for changes to take effect.[/yellow]")
        else:
            console.print("\n[dim]Run with --apply to make these changes[/dim]")

    elif generate:
        generated = handler.generate_static_entries()
        console.print("[blue]Generated static entries:[/blue]")
        console.print(generated)


# =====================
# Sync commands
# =====================

@main.group()
def sync() -> None:
    """Synchronize configurations between router and local."""
    pass


@sync.command("pull")
@click.argument("service", required=False)
@click.option("--all", "pull_all", is_flag=True, help="Pull all configs")
@click.pass_context
def pull_cmd(ctx: click.Context, service: Optional[str], pull_all: bool) -> None:
    """Pull configuration from router to local backup."""
    config = require_config()
    conn = require_connection(config)

    if pull_all or not service:
        console.print("[blue]Pulling all configurations...[/blue]")
        services_to_pull = ["dhcp", "firewall", "wireless", "network"]

        for svc in services_to_pull:
            from .uci.base import get_uci_handler
            handler = get_uci_handler(config, svc)
            handler.pull(conn)
            console.print(f"  [green]✓[/green] /etc/config/{svc}")

        # Pull AdGuard
        from .services.adguard import AdGuardDeployer
        deployer = AdGuardDeployer(config, conn)
        if deployer.pull():
            console.print(f"  [green]✓[/green] adguardhome.yaml")

        # Pull V2rayA
        from .services.v2raya import V2rayADeployer
        deployer = V2rayADeployer(config, conn)
        if deployer.pull():
            console.print(f"  [green]✓[/green] v2raya config")

    else:
        console.print(f"[blue]Pulling {service} configuration...[/blue]")
        if service == "adguard":
            from .services.adguard import AdGuardDeployer
            deployer = AdGuardDeployer(config, conn)
            deployer.pull()
        elif service == "v2raya":
            from .services.v2raya import V2rayADeployer
            deployer = V2rayADeployer(config, conn)
            deployer.pull()
        else:
            from .uci.base import get_uci_handler
            handler = get_uci_handler(config, service)
            handler.pull(conn)
        console.print(f"[green]✓ Pulled {service}[/green]")


@sync.command("push")
@click.argument("service", required=False)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.pass_context
def push_cmd(ctx: click.Context, service: Optional[str], dry_run: bool) -> None:
    """Push local configuration to router."""
    config = require_config()

    if not service:
        console.print("[red]Specify a service: adguard, v2raya, or uci config name[/red]")
        return

    conn = require_connection(config)

    if dry_run:
        console.print(f"[yellow]Would push {service} config to router[/yellow]")
        return

    console.print(f"[blue]Pushing {service} configuration...[/blue]")

    if service == "adguard":
        from .services.adguard import AdGuardDeployer
        deployer = AdGuardDeployer(config, conn)
        if deployer.push():
            console.print("[green]✓ Pushed and restarted AdGuard Home[/green]")
    elif service == "v2raya":
        from .services.v2raya import V2rayADeployer
        deployer = V2rayADeployer(config, conn)
        if deployer.push():
            console.print("[green]✓ Pushed V2rayA config[/green]")
    else:
        console.print(f"[red]Unknown service: {service}[/red]")


# =====================
# Deploy commands
# =====================

@main.group()
def deploy() -> None:
    """Deploy services to router."""
    pass


@deploy.command("run")
@click.argument("service", required=False)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.pass_context
def deploy_run(ctx: click.Context, service: Optional[str], dry_run: bool) -> None:
    """Deploy service(s) to router."""
    config = require_config()

    if service:
        services = [service]
    else:
        services = [name for name, cfg in config.services.items() if cfg.get("enabled", False)]

    if not services:
        console.print("[yellow]No services to deploy. Check inventory/config.yml[/yellow]")
        return

    console.print(f"[blue]Services to deploy: {', '.join(services)}[/blue]")

    conn = require_connection(config)

    for svc in services:
        if dry_run:
            console.print(f"\n[yellow]Dry run for {svc}:[/yellow]")
        else:
            console.print(f"\n[green]Deploying {svc}...[/green]")

        try:
            if svc == "adguard":
                from .services.adguard import AdGuardDeployer
                deployer = AdGuardDeployer(config, conn)
            elif svc == "v2raya":
                from .services.v2raya import V2rayADeployer
                deployer = V2rayADeployer(config, conn)
            elif svc == "core":
                from .services.core import CoreDeployer
                deployer = CoreDeployer(config, conn)
            else:
                console.print(f"[red]Unknown service: {svc}[/red]")
                continue

            deployer.deploy(dry_run=dry_run)
            if not dry_run:
                console.print(f"[green]✓ Deployed {svc}[/green]")

        except Exception as e:
            console.print(f"[red]Failed to deploy {svc}: {e}[/red]")


# =====================
# AdGuard commands
# =====================

@main.group()
def adguard() -> None:
    """AdGuard Home management."""
    pass


@adguard.command("clients")
@click.option("--apply", "apply_changes", is_flag=True, help="Apply to AdGuard config")
@click.pass_context
def adguard_clients(ctx: click.Context, apply_changes: bool) -> None:
    """Manage AdGuard clients from inventory/hosts.yml."""
    config = require_config()
    from .uci.dhcp import DHCPHandler

    handler = DHCPHandler(config)
    clients = handler.generate_adguard_clients()

    if not clients:
        console.print("[yellow]No clients defined in inventory/hosts.yml[/yellow]")
        return

    console.print(f"[blue]Generated {len(clients)} AdGuard clients:[/blue]\n")

    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("MAC", style="green")

    for client in clients:
        table.add_row(client["name"], client["ids"][0] if client["ids"] else "")

    console.print(table)

    if apply_changes:
        console.print("\n[yellow]Applying to AdGuard config...[/yellow]")
        conn = require_connection(config)

        from .services.adguard import AdGuardDeployer
        deployer = AdGuardDeployer(config, conn)

        if deployer.update_clients_from_inventory():
            console.print("[green]✓ AdGuard clients updated[/green]")
        else:
            console.print("[red]✗ Failed to update AdGuard clients[/red]")


# =====================
# Utils commands
# =====================

@main.group()
def utils() -> None:
    """Utility commands."""
    pass


@utils.command("exec")
@click.argument("command", required=True)
@click.pass_context
def exec_cmd(ctx: click.Context, command: str) -> None:
    """Execute command on router."""
    config = require_config()
    conn = require_connection(config)

    console.print(f"[blue]Running: {command}[/blue]")
    result = conn.run(command, check=False)
    console.print(result)


if __name__ == "__main__":
    main()
