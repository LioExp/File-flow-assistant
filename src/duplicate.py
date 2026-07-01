import os
import hashlib
import threading
from typing import List, Optional
from database import FileIndex

__all__ = ['DuplicateDetector']


class DuplicateDetector:
    def __init__(self, logger, watch_directories: List[str], hash_algo='sha256'):
        self.logger = logger
        self.watch_dirs = watch_directories
        self.hash_algo = hash_algo
        self.index = FileIndex()
        self._lock = threading.Lock()
        self._scan_done = threading.Event()
        self._duplicates = []
        self._seen_hashes = {}

    def start_background_scan(self):
        thread = threading.Thread(target=self._scan_existing_files, daemon=True)
        thread.start()
        return thread

    def wait_for_scan(self, timeout=None):
        self._scan_done.wait(timeout=timeout)

    def _scan_existing_files(self, progress=None, task_id=None):
        with self._lock:
            self.logger.info("Background scan started...")

            file_paths = []
            for directory in self.watch_dirs:
                if not os.path.isdir(directory):
                    self.logger.warning(f"Directory does not exist, skipping: {directory}")
                    continue
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_paths.append(os.path.join(root, file))

            total_files = len(file_paths)
            if total_files == 0:
                self.logger.info("No files found in monitored directories.")
                self._scan_done.set()
                return

            new_files = 0
            modified_files = 0
            unchanged_files = 0

            for path in file_paths:
                info = self.index.get_file_info(path)
                if info:
                    try:
                        current_mtime = os.path.getmtime(path)
                        stored_mtime = info['last_modified']
                        if isinstance(stored_mtime, (int, float)) and abs(stored_mtime - current_mtime) < 0.001:
                            unchanged_files += 1
                            self._seen_hashes[info['hash']] = path
                            if progress and task_id is not None:
                                progress.advance(task_id)
                            continue
                        else:
                            modified_files += 1
                    except OSError:
                        modified_files += 1
                else:
                    new_files += 1

                self._process_file(path)
                if progress and task_id is not None:
                    progress.advance(task_id)

            self.logger.info(
                f"Scan complete. Total: {total_files}, "
                f"New: {new_files}, Modified: {modified_files}, Unchanged: {unchanged_files}"
            )
            if self._duplicates:
                self.logger.warning(f"Found {len(self._duplicates)} duplicate files during scan.")
                for dup in self._duplicates:
                    self.logger.info(f"Duplicate: {dup['duplicate']} (original: {dup['original']})")

            self._scan_done.set()

    def _calculate_hash(self, file_path: str) -> Optional[str]:
        hash_func = hashlib.new(self.hash_algo)
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return None

    def _process_file(self, file_path: str):
        if not os.path.isfile(file_path):
            return

        stat = os.stat(file_path)
        size = stat.st_size
        mtime = stat.st_mtime
        file_hash = self._calculate_hash(file_path)
        if file_hash is None:
            return

        if file_hash in self._seen_hashes and self._seen_hashes[file_hash] != file_path:
            self._duplicates.append({
                'hash': file_hash,
                'original': self._seen_hashes[file_hash],
                'duplicate': file_path,
                'size': size
            })
        else:
            self._seen_hashes[file_hash] = file_path
            self.index.add_or_update(file_path, size, file_hash, mtime)

    def on_created(self, file_path: str):
        with self._lock:
            self._process_file(file_path)

    def on_modified(self, file_path: str):
        with self._lock:
            if self.index.path_exists(file_path):
                self.index.remove(file_path)
            self._process_file(file_path)

    def on_deleted(self, file_path: str):
        with self._lock:
            self.index.remove(file_path)

    def on_moved(self, src_path: str, dest_path: str):
        with self._lock:
            self.on_deleted(src_path)
            self.on_created(dest_path)

    def generate_report(self):
        with self._lock:
            return list(self._duplicates)
