import typer
import time
import os
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

app = typer.Typer()
console = Console()


def _logger():
    return ColoredLogger(log_file='logs/fileflow.log')


def _detector(logger=None):
    if logger is None:
        logger = _logger()
    return DuplicateDetector(logger, WATCH_DIRECTORIES)


@app.command()
def start():
    """Start FileFlow monitoring and duplicate detection."""
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

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping FileFlow...[/yellow]")
        observer.stop()

    observer.join()
    console.print("[green]Stopped with success![/green]")


@app.command()
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


@app.command()
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


@app.command()
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


@app.command()
def status():
    """Show system status and configuration."""
    data = get_status_data()

    table = Table(title="FileFlow Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Watch Directories", "\n".join(data['watch_directories']))
    table.add_row("Temp Base", data['temp_base'])
    table.add_row("Inactivity Hours", str(data['inactivity_hours']))
    table.add_row("Watch Delay (s)", str(data['watch_delay']))
    table.add_row("Recursive", str(data['recursive']))
    table.add_row("Indexed Files", str(data['indexed_files']) if data['indexed_files'] is not None else "?")
    table.add_row("Rules", str(data['rules_count']))

    console.print(table)


@app.command()
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


@app.command()
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


@app.command()
def recover(identifier: str):
    """Recover a file from FileFlow trash (use trash name or index number)."""
    dest, error = trash_recover(identifier)

    if error:
        console.print(f"[red]{error}[/red]")
        return

    console.print(f"[green]Recovered:[/green] {dest}")


@app.command()
def clean():
    """Remove expired files from FileFlow trash."""
    count = trash_clean()
    console.print(f"[green]Trash cleaned ({count} expired files removed).[/green]")


@app.command("watch")
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


@app.command("watch-add")
def watch_add(path: str):
    """Add a directory to monitor."""
    added, expanded, error = add_dir(path)
    if added:
        console.print(f"[green]Added:[/green] {expanded}")
    else:
        console.print(f"[yellow]{error}:[/yellow] {expanded}")


@app.command("watch-remove")
def watch_remove(path: str):
    """Remove a directory from monitoring."""
    removed, expanded, error = remove_dir(path)
    if removed:
        console.print(f"[green]Removed:[/green] {expanded}")
    else:
        console.print(f"[yellow]{error}:[/yellow] {expanded}")


@app.command("rules")
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


@app.command("rules-add")
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


@app.command("rules-remove")
def rules_remove(name: str):
    """Remove an organization rule by name."""
    remove_rule(name)
    console.print(f"[green]Rule removed:[/green] {name}")


@app.command()
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


@app.command()
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


@app.command()
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
