"""CLI interface for router deployer."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from .config import Config, get_config
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

    # Show hosts count
    hosts = config.hosts.get("hosts", {})
    console.print(f"\n[blue]Static Hosts:[/blue] {len(hosts)} configured")

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

    # Test connection
    require_connection(config)
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
@click.option("--remove-orphans", is_flag=True, help="Remove hosts not in inventory")
@click.option("--restart", is_flag=True, help="Restart dnsmasq after changes")
@click.option("--adguard", is_flag=True, help="Also update AdGuard clients")
@click.pass_context
def static_cmd(
    ctx: click.Context,
    preview: bool,
    apply_changes: bool,
    generate: bool,
    remove_orphans: bool,
    restart: bool,
    adguard: bool,
) -> None:
    """Manage static DHCP entries and optionally AdGuard clients."""
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

        if changes["to_remove"]:
            color = "red" if remove_orphans else "dim"
            action = "Will REMOVE" if remove_orphans else "Orphans (use --remove-orphans)"
            console.print(f"[{color}]{action} ({len(changes['to_remove'])}):[/{color}]")
            for h in changes["to_remove"]:
                console.print(f"  - {h['name']}: {h['mac']} -> {h['ip']}")

        if changes["unchanged"]:
            unchanged = ", ".join(changes["unchanged"])
            console.print(f"[dim]Unchanged ({len(changes['unchanged'])}): {unchanged}[/dim]")

        has_changes = (
            changes["to_add"] or
            changes["to_update"] or
            (changes["to_remove"] and remove_orphans)
        )
        if not has_changes and not adguard:
            console.print("[green]No changes needed[/green]")
            return

        if apply_changes:
            console.print("\n[yellow]Applying DHCP changes...[/yellow]")
            result = handler.apply_changes(
                conn,
                dry_run=False,
                remove_orphans=remove_orphans,
                restart_dnsmasq=restart,
            )

            if result.get("added"):
                console.print(f"[green]✓ Added: {', '.join(result['added'])}[/green]")
            if result.get("updated"):
                console.print(f"[green]✓ Updated: {', '.join(result['updated'])}[/green]")
            if result.get("removed"):
                console.print(f"[green]✓ Removed: {', '.join(result['removed'])}[/green]")
            if result.get("failed"):
                console.print(f"[red]✗ Failed: {result['failed']}[/red]")

            if restart:
                console.print("\n[green]✓ dnsmasq restarted[/green]")
            else:
                msg = "Run 'service dnsmasq restart' on router for changes to take effect."
                console.print(f"\n[yellow]{msg}[/yellow]")

        # Update AdGuard clients if requested
        if adguard:
            console.print("\n[yellow]Updating AdGuard clients...[/yellow]")
            from .services.adguard import AdGuardDeployer
            deployer = AdGuardDeployer(config, conn)
            if deployer.update_clients_from_inventory():
                console.print("[green]✓ AdGuard clients updated[/green]")
            else:
                console.print("[red]✗ Failed to update AdGuard clients[/red]")

        if not apply_changes and not adguard:
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
def pull_cmd(ctx: click.Context, service: str | None, pull_all: bool) -> None:
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
            console.print("  [green]✓[/green] adguardhome.yaml")

        # Pull V2rayA
        from .services.v2raya import V2rayADeployer
        deployer = V2rayADeployer(config, conn)
        if deployer.pull():
            console.print("  [green]✓[/green] v2raya config")

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
@click.option("--force", is_flag=True, help="Skip preview confirmation")
@click.pass_context
def push_cmd(ctx: click.Context, service: str | None, dry_run: bool, force: bool) -> None:
    """Push local configuration to router.

    For UCI configs (dhcp, firewall, wireless, network), shows a diff
    before pushing unless --force is used.
    """
    config = require_config()

    if not service:
        msg = "Specify a service: adguard, v2raya, dhcp, firewall, wireless, network"
        console.print(f"[red]{msg}[/red]")
        return

    conn = require_connection(config)

    if service == "adguard":
        if dry_run:
            console.print("[yellow]Would push AdGuard config and restart service[/yellow]")
            return
        console.print("[blue]Pushing AdGuard configuration...[/blue]")
        from .services.adguard import AdGuardDeployer
        deployer = AdGuardDeployer(config, conn)
        if deployer.push():
            console.print("[green]✓ Pushed and restarted AdGuard Home[/green]")

    elif service == "v2raya":
        if dry_run:
            console.print("[yellow]Would push V2rayA config[/yellow]")
            return
        console.print("[blue]Pushing V2rayA configuration...[/blue]")
        from .services.v2raya import V2rayADeployer
        deployer = V2rayADeployer(config, conn)
        if deployer.push():
            console.print("[green]✓ Pushed V2rayA config[/green]")

    elif service in ("dhcp", "firewall", "wireless", "network"):
        # Push UCI config with preview
        local_config = config.backups_dir / "router" / service
        if not local_config.exists():
            console.print(f"[red]No local backup found. Run 'sync pull {service}' first.[/red]")
            return

        local_content = local_config.read_text()
        remote_path = f"/etc/config/{service}"

        if dry_run:
            console.print(f"[yellow]Would push /etc/config/{service}[/yellow]")
            console.print(f"[dim]Local file size: {len(local_content)} bytes[/dim]")
            return

        # Show preview if not forced
        if not force:
            console.print(f"[blue]Preview for /etc/config/{service}:[/blue]")
            console.print(f"  Local file: {len(local_content)} bytes")

            # Get current remote content
            try:
                remote_content = conn.read_file(remote_path)
                console.print(f"  Remote file: {len(remote_content)} bytes")

                # Simple diff summary
                local_lines = local_content.strip().split("\n")
                remote_lines = remote_content.strip().split("\n")

                if local_content == remote_content:
                    console.print("[green]  Files are identical - no changes needed[/green]")
                    return

                msg = f"Local: {len(local_lines)} lines, Remote: {len(remote_lines)} lines"
                console.print(f"  [yellow]{msg}[/yellow]")

            except Exception:
                console.print("  [dim]Remote file not accessible[/dim]")

            console.print("\n[yellow]Run with --force to apply changes[/yellow]")
            return

        # Apply changes
        console.print(f"[blue]Pushing /etc/config/{service}...[/blue]")
        conn.write_file(remote_path, local_content, backup=True)
        console.print(f"[green]✓ Pushed /etc/config/{service}[/green]")
        console.print("[yellow]Restart services manually if needed[/yellow]")

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
def deploy_run(ctx: click.Context, service: str | None, dry_run: bool) -> None:
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
            elif svc == "filebrowser":
                from .services.filebrowser import FilebrowserDeployer
                deployer = FilebrowserDeployer(config, conn)
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
@click.option("--show-stderr", is_flag=True, help="Show stderr output")
@click.pass_context
def exec_cmd(ctx: click.Context, command: str, show_stderr: bool) -> None:
    """Execute command on router.

    Example:
        router utils exec "uptime"
        router utils exec "logread | tail -20" --show-stderr
    """
    config = require_config()
    conn = require_connection(config)

    console.print(f"[blue]Running: {command}[/blue]")
    result = conn.run(command, check=False)
    if result:
        console.print(result)

    if show_stderr:
        # Re-run with stderr capture
        import subprocess
        cmd = conn._build_ssh_cmd(command, 30)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if proc.stderr:
            console.print(f"[dim]stderr: {proc.stderr}[/dim]")


if __name__ == "__main__":
    main()
