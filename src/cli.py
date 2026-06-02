import typer
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

app = typer.Typer(help="FileFlow — intelligent file organizer")
console = Console()

BANNER = """
  ███████╗██╗██╗     ███████╗███████╗██╗      ██████╗ ██╗    ██╗
  ██╔════╝██║██║     ██╔════╝██╔════╝██║     ██╔═══██╗██║    ██║
  █████╗  ██║██║     █████╗  █████╗  ██║     ██║   ██║██║ █╗ ██║
  ██╔══╝  ██║██║     ██╔══╝  ██╔══╝  ██║     ██║   ██║██║███╗██║
  ██║     ██║███████╗███████╗██║     ███████╗╚██████╔╝╚███╔███╔╝
  ╚═╝     ╚═╝╚══════╝╚══════╝╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝
"""

# ─── Helpers visuais ──────────────────────────────────────────────────────────

def print_banner():
    console.print(Text(BANNER, style="bold cyan"))

def print_divider():
    console.print("[dim]────────────────────────────────────────────────────────[/dim]")

def ok(msg: str):
    console.print(f"[green]✓[/green] {msg}")

def warn(msg: str):
    console.print(f"[yellow]⚠[/yellow]  {msg}")

def err(msg: str):
    console.print(f"[red]✗[/red] {msg}")

def info(label: str, value: str):
    console.print(f"  [dim]{label}[/dim]  [cyan]{value}[/cyan]")

# ─── Comandos ─────────────────────────────────────────────────────────────────

@app.command()
def start():
    """Inicia o FileFlow Assistant."""
    # imports aqui para não quebrar se o módulo não existir ainda
    from config import (
        WATCH_DIRECTORIES, TEMP_BASE_DIR,
        TEMP_CATEGORIES, KEYWORD_PATTERNS,
        IGNORE_PATTERNS, TRIGGER_INACTIVITY_HOURS,
        WATCH_DELAY, WATCH_RECURSIVELY
    )
    from watcher import FileFlowHandler
    from watchdog.observers import Observer
    from logger import ColoredLogger
    from duplicate import DuplicateDetector
    from organizer import FileOrganizer
    import threading

    print_banner()
    print_divider()

    logger    = ColoredLogger(log_file="logs/fileflow.log")
    detector  = DuplicateDetector(logger, WATCH_DIRECTORIES)
    organizer = FileOrganizer(
        logger=logger,
        watch_dirs=WATCH_DIRECTORIES,
        temp_base=TEMP_BASE_DIR,
        categories=TEMP_CATEGORIES,
        patterns=KEYWORD_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        inactivity_hours=TRIGGER_INACTIVITY_HOURS
    )

    ok("FileFlow Assistant started")
    info("monitoring", "  ".join(WATCH_DIRECTORIES))
    info("trash     ", TEMP_BASE_DIR)
    info("inactivity", f"{TRIGGER_INACTIVITY_HOURS}h")
    print_divider()

    handler  = FileFlowHandler(logger, detector)
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
    ok("Stopped with success!")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
