# watcher.py
from watchdog.events import FileSystemEventHandler
import time

class FileFlowHandler(FileSystemEventHandler):
    def __init__(self, logger, detector):
        self.logger = logger
        self.detector = detector
        self.last_event = {}

    def on_created(self, event):
        if event.is_directory:
            return
        self.last_event[event.src_path] = ('created', time.time())
        self.logger.info("detected new file:", path=event.src_path)
        self.detector.check_new_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        last = self.last_event.get(event.src_path)
        if last and last[0] == 'created' and (time.time() - last[1]) < 0.5:
            return
        self.logger.info("detected modified file:", path=event.src_path)
        self.detector.check_modified_file(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self.logger.warning("detected deleted file:", path=event.src_path)
        self.detector.check_deleted_file(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        self.logger.info(f"detected moved file: from {event.src_path} to {event.dest_path}")
        # Para movimento, o arquivo mudou de caminho. Precisamos atualizar o detector.
        # A maneira mais simples: tratar como deleção no origem e criação no destino.
        self.detector.check_deleted_file(event.src_path)
        self.detector.check_new_file(event.dest_path)