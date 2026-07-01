import typer
import time
import os
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import (
    WATCH_DIRECTORIES, WATCH_RECURSIVELY,
    TRASH_DIR, METADATA_FILE
)
from watcher import FileFlowHandler
from watchdog.observers import Observer
from logger import ColoredLogger
from duplicate import DuplicateDetector
from organizer import FileOrganizer
from trash import clean_expired
from watch_config import load_dirs, add_dir, remove_dir
from rules import load_rules, add_rule, remove_rule
from scanner import VirusScanner
from services import (
    get_status_data, db_info, db_reset,
    trash_list, trash_recover, trash_clean, format_size
)

__all__ = ['app']

app = typer.Typer(
    callback=lambda: None,
    no_args_is_help=False,
    rich_markup_mode="rich",
)
console = Console()


def _show_dashboard():
    """Show dashboard when no command is provided."""
    from rich.text import Text
    from fileflow_mcp.config import load_mcp_config
    from config import FILEFLOW_HOME

    data = get_status_data()
    pid_file = FILEFLOW_HOME / "fileflow.pid"

    daemon_running = False
    daemon_pid = None
    daemon_uptime = None

    if pid_file.exists():
        try:
            daemon_pid = int(pid_file.read_text().strip())
            os.kill(daemon_pid, 0)
            daemon_running = True
            try:
                start_time = os.path.getmtime(str(pid_file))
                uptime_s = time.time() - start_time
                if uptime_s < 60:
                    daemon_uptime = f"{int(uptime_s)}s"
                elif uptime_s < 3600:
                    daemon_uptime = f"{int(uptime_s // 60)}m"
                else:
                    daemon_uptime = f"{int(uptime_s // 3600)}h {int((uptime_s % 3600) // 60)}m"
            except Exception:
                daemon_uptime = "?"
        except (ProcessLookupError, ValueError):
            daemon_pid = None

    mcp_config = load_mcp_config()
    mcp_enabled = mcp_config.get('enabled', False)

    trash_count = 0
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
            trash_count = len(metadata) if isinstance(metadata, dict) else 0
        except Exception:
            pass

    indexed = data['indexed_files'] or 0
    dirs_count = len(data['watch_directories'])

    # Header
    console.print()
    console.print("[bold]FileFlow[/bold]  [dim]---[/dim]")
    console.print()

    # Daemon
    if daemon_running:
        console.print(f"  [green]daemon[/green]  [bold]running[/bold]  [dim]{daemon_pid} | {daemon_uptime}[/dim]")
    else:
        console.print(f"  [red]daemon[/red]  [dim]stopped[/dim]  [dim]> fileflow start --daemon[/dim]")
    console.print()

    # Stats line
    stats = f"  [dim]{dirs_count} dirs  |  {indexed} files  |  {data['rules_count']} rules  |  {trash_count} trash[/dim]"
    console.print(stats)
    console.print()

    # MCP
    if mcp_enabled:
        console.print(f"  [green]mcp[/green]  [bold]active[/bold]")
    else:
        console.print(f"  [dim]mcp  off[/dim]")
    console.print()

    # Watched dirs
    if data['watch_directories']:
        console.print("  [dim]watching:[/dim]")
        for d in data['watch_directories'][:3]:
            console.print(f"    [dim]-[/dim] {d}")
        if dirs_count > 3:
            console.print(f"    [dim]- +{dirs_count - 3} more[/dim]")
        console.print()

    # Quick actions
    console.print("  [dim]---[/dim]")
    if not daemon_running:
        console.print("  [dim]>[/dim] [cyan]fileflow start --daemon[/cyan]  [dim]start monitoring[/dim]")
    else:
        console.print("  [dim]>[/dim] [cyan]fileflow stop[/cyan]  [dim]stop daemon[/dim]")
    if indexed == 0 and dirs_count > 0:
        console.print("  [dim]>[/dim] [cyan]fileflow scan[/cyan]  [dim]index files[/dim]")
    if trash_count > 0:
        console.print("  [dim]>[/dim] [cyan]fileflow trash[/cyan]  [dim]view trash[/dim]")
    console.print()


def _logger():
    return ColoredLogger(log_file='logs/fileflow.log')


def _detector(logger=None):
    if logger is None:
        logger = _logger()
    return DuplicateDetector(logger, WATCH_DIRECTORIES)


@app.command(rich_help_panel="[bold cyan]Core[/bold cyan]")
def start(
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run as background daemon"),
    mcp: bool = typer.Option(False, "--mcp", help="Enable MCP server"),
    port: int = typer.Option(8080, "--port", help="MCP server port (HTTP mode)"),
):
    """Start FileFlow monitoring and duplicate detection."""
    if daemon:
        _start_daemon()
        return

    _run_foreground(mcp=mcp)


def _run_foreground(mcp=False):
    logger = _logger()
    detector = _detector(logger)

    console.print("[bold cyan]FileFlow Assistant started![/bold cyan]")
    console.print(f"[dim]Monitoring:[/dim] {WATCH_DIRECTORIES}")

    detector.start_background_scan()
    console.print("[dim]Indexing files in background...[/dim]")

    handler = FileFlowHandler(logger, detector)
    observer = Observer()

    scheduled = 0
    for directory in WATCH_DIRECTORIES:
        if os.path.isdir(directory):
            observer.schedule(handler, directory, recursive=WATCH_RECURSIVELY)
            logger.info(f"Scheduled watching: {directory}")
            scheduled += 1
        else:
            console.print(f"[yellow]Skipping (not found):[/yellow] {directory}")

    if scheduled == 0:
        console.print("[red]No valid directories to watch. Use 'watch-add' to add one.[/red]")
        return

    observer.start()

    if mcp:
        from fileflow_mcp.server import create_fileflow_mcp
        from fileflow_mcp.security import create_policy
        from fileflow_mcp.config import load_mcp_config

        config = load_mcp_config()
        policy = create_policy(rate_limit=config.get('rate_limit', 60))
        for tool_name in config.get('blocked_tools', []):
            policy.block_tool(tool_name)

        fileflow_mcp = create_fileflow_mcp(security=policy)
        console.print(f"[bold cyan]MCP server enabled![/bold cyan]")
        console.print(f"[dim]Transport:[/dim] stdio (use with Claude Code, Cursor, etc.)")

        import threading
        def run_mcp():
            fileflow_mcp.run(transport="stdio")

        mcp_thread = threading.Thread(target=run_mcp, daemon=True)
        mcp_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping FileFlow...[/yellow]")
        observer.stop()

    observer.join()
    console.print("[green]Stopped with success![/green]")


def _start_daemon():
    import signal
    import sys
    from config import FILEFLOW_HOME

    pid_file = FILEFLOW_HOME / "fileflow.pid"
    log_file = FILEFLOW_HOME / "fileflow.log"

    if pid_file.exists():
        old_pid = pid_file.read_text().strip()
        try:
            os.kill(int(old_pid), 0)
            console.print(f"[yellow]FileFlow already running (PID {old_pid}).[/yellow]")
            console.print("[dim]Use 'fileflow stop' to stop it.[/dim]")
            return
        except (ProcessLookupError, ValueError):
            pid_file.unlink()

    pid = os.fork()
    if pid > 0:
        console.print(f"[green]FileFlow daemon started (PID {pid})[/green]")
        console.print(f"[dim]Log: {log_file}[/dim]")
        console.print("[dim]Stop with: fileflow stop[/dim]")
        return

    os.setsid()

    sys.stdin = open(os.devnull, 'r')
    sys.stdout = open(log_file, 'a')
    sys.stderr = open(log_file, 'a')

    FILEFLOW_HOME.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))

    def cleanup(signum, frame):
        if pid_file.exists():
            pid_file.unlink()
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    _run_foreground(mcp=False)


@app.command(rich_help_panel="[bold green]Files[/bold green]")
def scan():
    """Scan for duplicate files and display results."""
    logger = _logger()
    detector = _detector(logger)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task("Scanning files...", total=None)
        detector._scan_existing_files()

    duplicates = detector.generate_report()

    if not duplicates:
        console.print("[green]No duplicates found![/green]")
        return

    table = Table(title=f"Duplicates Found ({len(duplicates)})")
    table.add_column("File", style="yellow")
    table.add_column("Same as", style="dim")
    table.add_column("Size", style="cyan")

    for dup in duplicates:
        table.add_row(dup['duplicate'], dup['original'], format_size(dup['size']))

    console.print(table)


@app.command(rich_help_panel="[bold green]Files[/bold green]")
def organize():
    """Preview and organize inactive files."""
    from config import (
        TEMP_BASE_DIR, TEMP_CATEGORIES,
        KEYWORD_PATTERNS, IGNORE_PATTERNS,
        TRIGGER_INACTIVITY_HOURS
    )

    organizer = FileOrganizer(
        logger=_logger(),
        watch_dirs=WATCH_DIRECTORIES,
        temp_base=TEMP_BASE_DIR,
        categories=TEMP_CATEGORIES,
        patterns=KEYWORD_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        inactivity_hours=TRIGGER_INACTIVITY_HOURS
    )
    files = organizer.preview(recursive=WATCH_RECURSIVELY)

    if not files:
        console.print("[green]No inactive files to organize.[/green]")
        return

    table = Table(title=f"Files to organize ({len(files)})")
    table.add_column("File", style="yellow")
    table.add_column("Category", style="cyan")
    table.add_column("Size", style="dim")
    table.add_column("Destination", style="green")

    for f in files:
        table.add_row(
            f['source'].name,
            f['category'],
            format_size(f['size']),
            str(f['dest'].parent)
        )

    console.print(table)

    if not typer.confirm("Do you want to organize these files?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("Moving files...", total=len(files))
        for f in files:
            organizer.organize_file(f['source'])
            progress.advance(task)

    console.print(f"[green]Organized {len(files)} files.[/green]")


@app.command(rich_help_panel="[bold green]Files[/bold green]")
def report():
    """Generate a duplicate report file."""
    logger = _logger()
    detector = _detector(logger)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task("Scanning files...", total=None)
        detector._scan_existing_files()

    duplicates = detector.generate_report()

    if not duplicates:
        console.print("[green]No duplicates to report![/green]")
        return

    report_path = f"duplicates_report_{int(time.time())}.txt"
    with open(report_path, 'w') as f:
        for dup in duplicates:
            f.write(f"Duplicate: {dup['duplicate']}\n")
            f.write(f"Original:  {dup['original']}\n")
            f.write(f"Hash:      {dup['hash']}\n")
            f.write(f"Size:      {format_size(dup['size'])}\n")
            f.write("-" * 60 + "\n")

    console.print(f"[green]Report saved to[/green] [bold]{report_path}[/bold]")


@app.command(rich_help_panel="[bold cyan]Core[/bold cyan]")
def status():
    """Show complete FileFlow dashboard."""
    _show_dashboard()


@app.command(rich_help_panel="[yellow]Management[/yellow]")
def db(action: str = typer.Argument("info", help="info | reset")):
    """Database operations (info or reset)."""
    if action == "info":
        info = db_info()
        if info['error']:
            console.print(f"[red]Error:[/red] {info['error']}")
        else:
            console.print(f"[cyan]Database:[/cyan] {info['path']}")
            console.print(f"[cyan]Indexed files:[/cyan] [bold]{info['count']}[/bold]")

    elif action == "reset":
        if typer.confirm("Are you sure you want to reset the database?"):
            db_reset()
            console.print("[green]Database reset![/green]")

    else:
        console.print(f"[red]Unknown action: {action}. Use 'info' or 'reset'.[/red]")


@app.command(rich_help_panel="[bold green]Files[/bold green]")
def trash():
    """Show files in FileFlow trash."""
    items = trash_list()

    if items is None:
        console.print("[green]Trash is empty.[/green]")
        return

    if not items:
        console.print("[green]Trash is empty.[/green]")
        return

    table = Table(title=f"FileFlow Trash ({len(items)} files)")
    table.add_column("#", style="dim")
    table.add_column("Trash Name", style="yellow")
    table.add_column("Original Path", style="dim")
    table.add_column("Deleted At", style="cyan")

    for i, item in enumerate(items, 1):
        table.add_row(str(i), item['trash_name'], item['original_path'], item['deleted_at'])

    console.print(table)


@app.command(rich_help_panel="[bold green]Files[/bold green]")
def recover(identifier: str):
    """Recover a file from FileFlow trash (use trash name or index number)."""
    dest, error = trash_recover(identifier)

    if error:
        console.print(f"[red]{error}[/red]")
        return

    console.print(f"[green]Recovered:[/green] {dest}")


@app.command(rich_help_panel="[bold green]Files[/bold green]")
def clean():
    """Remove expired files from FileFlow trash."""
    count = trash_clean()
    console.print(f"[green]Trash cleaned ({count} expired files removed).[/green]")


@app.command("watch", rich_help_panel="[yellow]Management[/yellow]")
def watch_list():
    """List monitored directories."""
    dirs = load_dirs()

    if not dirs:
        console.print("[yellow]No directories configured.[/yellow]")
        return

    table = Table(title="Monitored Directories")
    table.add_column("#", style="dim")
    table.add_column("Path", style="cyan")
    table.add_column("Exists", style="green")

    for i, d in enumerate(dirs, 1):
        exists = "yes" if os.path.isdir(d) else "[red]no[/red]"
        table.add_row(str(i), d, exists)

    console.print(table)


@app.command("watch-add", rich_help_panel="[yellow]Management[/yellow]")
def watch_add(path: str):
    """Add a directory to monitor."""
    added, expanded, error = add_dir(path)
    if added:
        console.print(f"[green]Added:[/green] {expanded}")
    else:
        console.print(f"[yellow]{error}:[/yellow] {expanded}")


@app.command("watch-remove", rich_help_panel="[yellow]Management[/yellow]")
def watch_remove(path: str):
    """Remove a directory from monitoring."""
    removed, expanded, error = remove_dir(path)
    if removed:
        console.print(f"[green]Removed:[/green] {expanded}")
    else:
        console.print(f"[yellow]{error}:[/yellow] {expanded}")


@app.command("rules", rich_help_panel="[yellow]Management[/yellow]")
def rules_list():
    """List organization rules."""
    rules = load_rules()

    if not rules:
        console.print("[yellow]No rules configured.[/yellow]")
        return

    table = Table(title="Organization Rules")
    table.add_column("Name", style="yellow")
    table.add_column("Conditions", style="cyan")
    table.add_column("Action", style="green")

    for r in rules:
        conds = ", ".join(f"{k}={v}" for k, v in r.conditions.items())
        action = f"{r.action['type']} -> {r.action['dest']}"
        table.add_row(r.name, conds, action)

    console.print(table)


@app.command("rules-add", rich_help_panel="[yellow]Management[/yellow]")
def rules_add(
    name: str,
    extension: str = typer.Option(None, help="File extension (e.g. .pdf)"),
    keyword: str = typer.Option(None, help="Keyword in filename"),
    dest: str = typer.Option(..., help="Destination category"),
):
    """Add an organization rule."""
    conditions = {}
    if extension:
        conditions['extension'] = extension.lower()
    if keyword:
        conditions['keyword'] = keyword

    if not conditions:
        console.print("[red]Provide at least --extension or --keyword.[/red]")
        return

    action = {"type": "move", "dest": dest}
    add_rule(name, conditions, action)
    console.print(f"[green]Rule added:[/green] {name}")


@app.command("rules-remove", rich_help_panel="[yellow]Management[/yellow]")
def rules_remove(name: str):
    """Remove an organization rule by name."""
    remove_rule(name)
    console.print(f"[green]Rule removed:[/green] {name}")


@app.command(rich_help_panel="[red]Security[/red]")
def scanfile(file: str):
    """Scan a single file for malware."""
    scanner = VirusScanner()

    if not scanner.is_available():
        console.print("[red]No antivirus found.[/red]")
        console.print("[dim]Install ClamAV (Linux): sudo apt install clamav[/dim]")
        console.print("[dim]Windows Defender is built-in on Windows.[/dim]")
        return

    console.print(f"[dim]Using:[/dim] {scanner.get_backend_name()}")
    console.print(f"[dim]Scanning:[/dim] {file}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task("Scanning...", total=None)
        result = scanner.scan_file(file)

    if result['status'] == 'clean':
        console.print(f"[green]CLEAN[/green] - {file}")
    elif result['status'] == 'infected':
        console.print(f"[bold red]INFECTED![/bold red] - {file}")
        console.print(f"[red]Threat:[/red] {result.get('threat', 'unknown')}")
    elif result['status'] == 'error':
        console.print(f"[yellow]ERROR[/yellow] - {result.get('message', 'unknown')}")
    elif result['status'] == 'unavailable':
        console.print(f"[red]Scanner unavailable:[/red] {result.get('message', '')}")


@app.command(rich_help_panel="[red]Security[/red]")
def scandir(dir: str = typer.Argument(".", help="Directory to scan")):
    """Scan a directory for malware."""
    scanner = VirusScanner()

    if not scanner.is_available():
        console.print("[red]No antivirus found.[/red]")
        console.print("[dim]Install ClamAV (Linux): sudo apt install clamav[/dim]")
        console.print("[dim]Windows Defender is built-in on Windows.[/dim]")
        return

    console.print(f"[dim]Using:[/dim] {scanner.get_backend_name()}")
    console.print(f"[dim]Scanning:[/dim] {dir}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task("Scanning directory...", total=None)
        results = scanner.scan_directory(dir)

    clean = sum(1 for r in results if r['status'] == 'clean')
    infected = [r for r in results if r['status'] == 'infected']
    errors = sum(1 for r in results if r['status'] == 'error')

    console.print(f"\n[green]Clean:[/green] {clean}")
    console.print(f"[red]Infected:[/red] {len(infected)}")
    if errors:
        console.print(f"[yellow]Errors:[/yellow] {errors}")

    if infected:
        console.print("\n[bold red]INFECTED FILES:[/bold red]")
        for r in infected:
            console.print(f"  [red]{r['file']}[/red] - {r.get('threat', 'unknown')}")


@app.command(rich_help_panel="[red]Security[/red]")
def scanwatch():
    """Scan all monitored directories for malware."""
    scanner = VirusScanner()

    if not scanner.is_available():
        console.print("[red]No antivirus found.[/red]")
        console.print("[dim]Install ClamAV (Linux): sudo apt install clamav[/dim]")
        console.print("[dim]Windows Defender is built-in on Windows.[/dim]")
        return

    console.print(f"[dim]Using:[/dim] {scanner.get_backend_name()}")
    console.print(f"[dim]Scanning monitored directories:[/dim] {WATCH_DIRECTORIES}")

    total_clean = 0
    total_infected = []

    for directory in WATCH_DIRECTORIES:
        if not os.path.isdir(directory):
            console.print(f"[yellow]Skipping (not found):[/yellow] {directory}")
            continue

        console.print(f"\n[bold]Scanning {directory}...[/bold]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            progress.add_task(f"Scanning {directory}...", total=None)
            results = scanner.scan_directory(directory)

        for r in results:
            if r['status'] == 'clean':
                total_clean += 1
            elif r['status'] == 'infected':
                total_infected.append(r)

    console.print(f"\n{'='*50}")
    console.print(f"[green]Total clean:[/green] {total_clean}")
    console.print(f"[red]Total infected:[/red] {len(total_infected)}")

    if total_infected:
        console.print("\n[bold red]INFECTED FILES:[/bold red]")
        for r in total_infected:
            console.print(f"  [red]{r['file']}[/red] - {r.get('threat', 'unknown')}")


@app.command("mcp", rich_help_panel="[dim]Advanced[/dim]")
def mcp_status():
    """Show MCP server configuration."""
    from fileflow_mcp.config import load_mcp_config
    config = load_mcp_config()

    table = Table(title="MCP Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Enabled", str(config.get('enabled', False)))
    table.add_row("Transport", config.get('transport', 'stdio'))
    table.add_row("Port", str(config.get('port', 8080)))
    table.add_row("Rate Limit", f"{config.get('rate_limit', 60)}/min")
    table.add_row("Audit Log", str(config.get('log_audit', True)))
    table.add_row("Blocked Tools", ", ".join(config.get('blocked_tools', [])) or "none")

    console.print(table)


@app.command("mcp-enable", rich_help_panel="[dim]Advanced[/dim]")
def mcp_enable():
    """Enable MCP server."""
    from fileflow_mcp.config import load_mcp_config, save_mcp_config
    config = load_mcp_config()
    config['enabled'] = True
    save_mcp_config(config)
    console.print("[green]MCP server enabled.[/green]")
    console.print("[dim]Use 'fileflow start --mcp' to start with MCP.[/dim]")


@app.command("mcp-disable", rich_help_panel="[dim]Advanced[/dim]")
def mcp_disable():
    """Disable MCP server."""
    from fileflow_mcp.config import load_mcp_config, save_mcp_config
    config = load_mcp_config()
    config['enabled'] = False
    save_mcp_config(config)
    console.print("[green]MCP server disabled.[/green]")


@app.command("mcp-audit", rich_help_panel="[dim]Advanced[/dim]")
def mcp_audit(lines: int = typer.Option(20, "--lines", help="Number of recent entries")):
    """Show MCP audit log."""
    from config import FILEFLOW_HOME
    audit_file = FILEFLOW_HOME / "mcp_audit.jsonl"

    if not audit_file.exists():
        console.print("[yellow]No audit log found.[/yellow]")
        return

    with open(audit_file, 'r') as f:
        entries = f.readlines()

    recent = entries[-lines:]

    table = Table(title=f"MCP Audit Log (last {len(recent)})")
    table.add_column("Time", style="dim")
    table.add_column("Tool", style="cyan")
    table.add_column("Args", style="yellow")
    table.add_column("Result", style="green")
    table.add_column("Error", style="red")

    for entry in recent:
        try:
            e = __import__('json').loads(entry)
            table.add_row(
                e.get('timestamp', '?')[:19],
                e.get('tool', '?'),
                str(e.get('args', {}))[:40],
                str(e.get('result', ''))[:40],
                "yes" if e.get('error') else ""
            )
        except Exception:
            continue

    console.print(table)


@app.command(rich_help_panel="[bold cyan]Core[/bold cyan]")
def stop():
    """Stop the FileFlow daemon."""
    import signal
    from config import FILEFLOW_HOME
    pid_file = FILEFLOW_HOME / "fileflow.pid"

    if not pid_file.exists():
        console.print("[yellow]No FileFlow daemon running.[/yellow]")
        return

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        try:
            os.kill(pid, 0)
            console.print(f"[yellow]Process {pid} still alive, sending SIGKILL...[/yellow]")
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        pid_file.unlink()
        console.print(f"[green]FileFlow daemon stopped (PID {pid}).[/green]")
    except ProcessLookupError:
        console.print("[yellow]Daemon process not found, cleaning up PID file.[/yellow]")
        pid_file.unlink()
    except Exception as e:
        console.print(f"[red]Error stopping daemon: {e}[/red]")


@app.command(rich_help_panel="[bold cyan]Core[/bold cyan]")
def daemon_status():
    """Check if FileFlow daemon is running."""
    from config import FILEFLOW_HOME
    pid_file = FILEFLOW_HOME / "fileflow.pid"
    log_file = FILEFLOW_HOME / "fileflow.log"

    if not pid_file.exists():
        console.print("[yellow]FileFlow daemon is not running.[/yellow]")
        return

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        console.print(f"[green]FileFlow daemon is running (PID {pid}).[/green]")
        console.print(f"[dim]Log: {log_file}[/dim]")
    except ProcessLookupError:
        console.print("[yellow]FileFlow daemon is not running (stale PID file).[/yellow]")
        pid_file.unlink()
    except ValueError:
        console.print("[red]Invalid PID file.[/red]")
        pid_file.unlink()


@app.command(rich_help_panel="[bold cyan]Core[/bold cyan]")
def restart():
    """Restart the FileFlow daemon."""
    stop()
    time.sleep(1)
    _start_daemon()


@app.command("service-install", rich_help_panel="[dim]Advanced[/dim]")
def service_install():
    """Install FileFlow as a systemd service (Linux)."""
    import subprocess
    from config import FILEFLOW_HOME

    venv_python = str(Path(__file__).parent.parent / "venv" / "bin" / "python")
    main_py = str(Path(__file__).parent / "main.py")

    if not os.path.exists(venv_python):
        console.print("[red]Virtual environment not found.[/red]")
        console.print(f"[dim]Expected: {venv_python}[/dim]")
        return

    service_content = f"""[Unit]
Description=FileFlow - Intelligent File Organizer
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={str(Path(__file__).parent.parent)}
ExecStart={venv_python} {main_py} start
Restart=on-failure
RestartSec=10
StandardOutput=append:{FILEFLOW_HOME / 'fileflow.log'}
StandardError=append:{FILEFLOW_HOME / 'fileflow.log'}

[Install]
WantedBy=multi-user.target
"""

    service_path = Path.home() / ".config" / "systemd" / "user" / "fileflow.service"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    service_path.write_text(service_content)

    console.print(f"[green]Service file created:[/green] {service_path}")
    console.print("")
    console.print("[bold]To activate:[/bold]")
    console.print(f"  systemctl --user daemon-reload")
    console.print(f"  systemctl --user enable fileflow")
    console.print(f"  systemctl --user start fileflow")
    console.print("")
    console.print("[bold]Commands:[/bold]")
    console.print(f"  systemctl --user status fileflow")
    console.print(f"  systemctl --user stop fileflow")
    console.print(f"  journalctl --user -u fileflow -f")


@app.command("service-uninstall", rich_help_panel="[dim]Advanced[/dim]")
def service_uninstall():
    """Uninstall the FileFlow systemd service."""
    import subprocess

    service_path = Path.home() / ".config" / "systemd" / "user" / "fileflow.service"

    subprocess.run(["systemctl", "--user", "stop", "fileflow"], capture_output=True)
    subprocess.run(["systemctl", "--user", "disable", "fileflow"], capture_output=True)

    if service_path.exists():
        service_path.unlink()

    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)

    console.print("[green]FileFlow service uninstalled.[/green]")
