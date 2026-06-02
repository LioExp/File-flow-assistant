import typer
import threading
import time
import os
import sqlite3
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from config import (
    WATCH_DIRECTORIES, TEMP_BASE_DIR, TEMP_CATEGORIES,
    KEYWORD_PATTERNS, IGNORE_PATTERNS,
    TRIGGER_INACTIVITY_HOURS, WATCH_DELAY, WATCH_RECURSIVELY
)
from watcher import FileFlowHandler
from watchdog.observers import Observer
from logger import ColoredLogger
from duplicate import DuplicateDetector
from organizer import FileOrganizer
from database import FileIndex

app = typer.Typer()
console = Console()


def _logger():
    return ColoredLogger(log_file='logs/fileflow.log')


def _detector(logger=None):
    if logger is None:
        logger = _logger()
    return DuplicateDetector(logger, WATCH_DIRECTORIES)


def _organizer(logger=None):
    if logger is None:
        logger = _logger()
    return FileOrganizer(
        logger=logger,
        watch_dirs=WATCH_DIRECTORIES,
        temp_base=TEMP_BASE_DIR,
        categories=TEMP_CATEGORIES,
        patterns=KEYWORD_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        inactivity_hours=TRIGGER_INACTIVITY_HOURS
    )


@app.command()
def start():
    """Start FileFlow monitoring and auto-organizing."""
    logger = _logger()
    detector = _detector(logger)
    organizer = _organizer(logger)

    console.print("[bold cyan]FileFlow Assistant started![/bold cyan]")
    console.print(f"[dim]Monitoring:[/dim] {WATCH_DIRECTORIES}")
    console.print(f"[dim]Temp folder:[/dim] {TEMP_BASE_DIR}")
    console.print(f"[dim]Organizing files older than[/dim] [yellow]{TRIGGER_INACTIVITY_HOURS}h[/yellow]")

    handler = FileFlowHandler(logger, detector)
    observer = Observer()

    for pasta in WATCH_DIRECTORIES:
        observer.schedule(handler, pasta, recursive=WATCH_RECURSIVELY)
        logger.info(f"Scheduled watching: {pasta}")

    observer.start()

    def organizer_loop():
        while True:
            time.sleep(WATCH_DELAY)
            organizer.scan_and_organize(recursive=WATCH_RECURSIVELY)

    threading.Thread(target=organizer_loop, daemon=True).start()

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
    duplicates = detector.generate_report()

    if not duplicates:
        console.print("[green]No duplicates found![/green]")
        return

    table = Table(title=f"Duplicates Found ({len(duplicates)})")
    table.add_column("Duplicate", style="yellow")
    table.add_column("Original", style="dim")
    table.add_column("Size (bytes)", style="cyan")

    for dup in duplicates:
        table.add_row(dup['duplicate'], dup['original'], str(dup['size']))

    console.print(table)


@app.command()
def organize():
    """Run one-time organization of inactive files."""
    logger = _logger()
    organizer = _organizer(logger)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        progress.add_task("Organizing inactive files...", total=None)
        organizer.scan_and_organize(recursive=WATCH_RECURSIVELY)

    console.print("[green]Organization complete![/green]")


@app.command()
def report():
    """Generate a duplicate report file."""
    logger = _logger()
    detector = _detector(logger)
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
            f.write(f"Size:      {dup['size']} bytes\n")
            f.write("-" * 60 + "\n")

    console.print(f"[green]Report saved to[/green] [bold]{report_path}[/bold]")


@app.command()
def status():
    """Show system status and configuration."""
    table = Table(title="FileFlow Status")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Watch Directories", "\n".join(WATCH_DIRECTORIES))
    table.add_row("Temp Base", TEMP_BASE_DIR)
    table.add_row("Inactivity Hours", str(TRIGGER_INACTIVITY_HOURS))
    table.add_row("Watch Delay (s)", str(WATCH_DELAY))
    table.add_row("Recursive", str(WATCH_RECURSIVELY))
    table.add_row("Categories", str(len(TEMP_CATEGORIES)))

    index = FileIndex()
    try:
        with sqlite3.connect(index.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        table.add_row("Indexed Files", str(count))
    except Exception:
        table.add_row("Indexed Files", "?")

    console.print(table)


@app.command()
def db(action: str = typer.Argument("info", help="info | reset")):
    """Database operations (info or reset)."""
    index = FileIndex()

    if action == "info":
        try:
            with sqlite3.connect(index.db_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            console.print(f"[cyan]Database:[/cyan] {index.db_path}")
            console.print(f"[cyan]Indexed files:[/cyan] [bold]{count}[/bold]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

    elif action == "reset":
        if typer.confirm("Are you sure you want to reset the database?"):
            if os.path.exists(index.db_path):
                os.remove(index.db_path)
            FileIndex(index.db_path)._init_db()
            console.print("[green]Database reset![/green]")

    else:
        console.print(f"[red]Unknown action: {action}. Use 'info' or 'reset'.[/red]")
