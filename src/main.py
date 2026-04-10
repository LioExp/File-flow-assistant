from config import (
    WATCH_DIRECTORIES,
    TEMP_BASE_DIR,
    TEMP_CATEGORIES,
    KEYWORD_PATTERNS,
    IGNORE_PATTERNS,
    TRIGGER_INACTIVITY_HOURS,
    WATCH_DELAY,
    WATCH_RECURSIVELY
)
from watcher import FileFlowHandler
from watchdog.observers import Observer
from logger import ColoredLogger
from duplicate import DuplicateDetector
from organizer import FileOrganizer
import threading
import time

if __name__ == "__main__":
    # 1. Logger
    logger = ColoredLogger(log_file='logs/fileflow.log')

    # 2. Detector de duplicatas
    detector = DuplicateDetector(logger, WATCH_DIRECTORIES)

    # 3. Organizador de arquivos inativos
    organizer = FileOrganizer(
        logger=logger,
        watch_dirs=WATCH_DIRECTORIES,
        temp_base=TEMP_BASE_DIR,
        categories=TEMP_CATEGORIES,
        patterns=KEYWORD_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        inactivity_hours=TRIGGER_INACTIVITY_HOURS
    )

    print("File Flow Assistant started!")
    print(f"Monitoring: {WATCH_DIRECTORIES}")
    print(f"Temp folder: {TEMP_BASE_DIR}")
    print(f"Organizing files older than {TRIGGER_INACTIVITY_HOURS} hours")

    # 4. Handler e Observer
    handler = FileFlowHandler(logger, detector)
    observer = Observer()

    for pasta in WATCH_DIRECTORIES:
        observer.schedule(handler, pasta, recursive=WATCH_RECURSIVELY)
        logger.info(f"Scheduled watching: {pasta}")

    observer.start()

    # 5. Thread do organizador (roda em background)
    def organizer_loop():
        while True:
            time.sleep(WATCH_DELAY)
            organizer.scan_and_organize(recursive=WATCH_RECURSIVELY)

    org_thread = threading.Thread(target=organizer_loop, daemon=True)
    org_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping the File Flow Assistant...")
        observer.stop()
    observer.join()
    print("Stopped with success!")