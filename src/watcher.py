from watchdog.events import FileSystemEventHandler
import time
import sys


class FileFlowHandler(FileSystemEventHandler):
    def __init__(self, logger, detector):
        self.logger = logger
        self.detector = detector
        self.last_event = {}
        self._debounce_ms = 500 if sys.platform == 'win32' else 500

    def on_created(self, event):
        if event.is_directory:
            return
        self.last_event[event.src_path] = ('created', time.time())
        self.logger.info("detected new file:", path=event.src_path)
        self.detector.on_created(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        last = self.last_event.get(event.src_path)
        if last and last[0] == 'created' and (time.time() - last[1]) < 0.5:
            return
        self.logger.info("detected modified file:", path=event.src_path)
        self.detector.on_modified(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self.logger.warning("detected deleted file:", path=event.src_path)
        self.detector.on_deleted(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        self.logger.info(f"detected moved file: from {event.src_path} to {event.dest_path}")
        self.detector.on_moved(event.src_path, event.dest_path)