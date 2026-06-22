import os
import hashlib
import threading
from typing import List, Optional
from database import FileIndex
from datetime import datetime
from progress import ProgressBar
from config import GREEN


class DuplicateDetector:
    def __init__(self, logger, watch_directories: List[str], hash_algo='sha256'):
        self.logger = logger
        self.watch_dirs = watch_directories
        self.hash_algo = hash_algo
        self.index = FileIndex()
        self.duplicates_report = []
        self._scan_lock = threading.Lock()
        self._scan_done = threading.Event()

    def start_background_scan(self):
        thread = threading.Thread(target=self._scan_existing_files, daemon=True)
        thread.start()
        return thread

    def wait_for_scan(self, timeout=None):
        self._scan_done.wait(timeout=timeout)

    def _scan_existing_files(self):
        with self._scan_lock:
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

            bar = ProgressBar(total=total_files, prefix="Indexing", color=GREEN)

            new_files = 0
            modified_files = 0
            unchanged_files = 0

            for path in file_paths:
                info = self.index.get_file_info(path)
                if info:
                    try:
                        current_mtime = os.path.getmtime(path)
                        current_mtime_str = datetime.fromtimestamp(current_mtime).isoformat()
                        if info['last_modified'] == current_mtime_str:
                            unchanged_files += 1
                            bar.update()
                            continue
                        else:
                            modified_files += 1
                    except OSError:
                        modified_files += 1
                else:
                    new_files += 1

                self._process_file(path)
                bar.update()

            self.logger.info(
                f"Scan complete. Total: {total_files}, "
                f"New: {new_files}, Modified: {modified_files}, Unchanged: {unchanged_files}"
            )
            if self.duplicates_report:
                self.logger.warning(f"Found {len(self.duplicates_report)} duplicate files during scan.")
                for dup in self.duplicates_report:
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
        mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
        file_hash = self._calculate_hash(file_path)
        if file_hash is None:
            return

        existing = self.index.get_all_hashes()
        if file_hash in existing and existing[file_hash] != file_path:
            self.duplicates_report.append({
                'hash': file_hash,
                'original': existing[file_hash],
                'duplicate': file_path,
                'size': size
            })
            # Não logar durante varredura para não poluir a barra
            # self.logger.warning(f"Duplicate detected: {file_path} (same as {existing[file_hash]})")
        else:
            self.index.add_or_update(file_path, size, file_hash, mtime)

    def on_created(self, file_path: str):
        self._process_file(file_path)

    def on_modified(self, file_path: str):
        if self.index.path_exists(file_path):
            self.index.remove(file_path)
        self._process_file(file_path)

    def on_deleted(self, file_path: str):
        self.index.remove(file_path)

    def on_moved(self, src_path: str, dest_path: str):
        self.on_deleted(src_path)
        self.on_created(dest_path)

    def generate_report(self):
        return self.duplicates_report
