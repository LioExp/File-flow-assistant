from config import WATCH_DIRECTORIES
from watcher import FileFlowHandler
from watchdog.observers import Observer
from logger import ColoredLogger
from duplicate import DuplicateDetector
import time

if __name__ == "__main__":
    #create the logger (with files log optional)
    logger = ColoredLogger(log_file='logs/fileflow.log')
    
    #Cria o detector de duplicatas (passando o logger e as pastas monitoradas)
    detector = DuplicateDetector(logger, WATCH_DIRECTORIES)
    
    print("File Flow Assistant started!")
    print(f"Monitoring: {WATCH_DIRECTORIES}")

    # Passa o logger E o detector para o handler
    handler = FileFlowHandler(logger, detector)
    observer = Observer()

    for pasta in WATCH_DIRECTORIES:
        observer.schedule(handler, pasta, recursive=False)
        logger.info(f"Scheduled watching: {pasta}")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping the File Flow Assistant...")
        observer.stop()
    observer.join()
    print("Stopped with success!")