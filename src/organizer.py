import os
import shutil
import time
from pathlib import Path


class FileOrganizer:
    def __init__(self, logger, watch_dirs, temp_base, categories, patterns, ignore_patterns, inactivity_hours):
        self.logger = logger
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.temp_base = Path(temp_base)
        self.categories = categories
        self.patterns = patterns
        self.ignore_patterns = ignore_patterns
        self.inactivity_hours = inactivity_hours

    def _should_ignore(self, file_path):
        file_str = str(file_path).lower()
        for pattern in self.ignore_patterns:
            if pattern.lower() in file_str:
                return True
        return False

    def _get_category(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.categories:
            return self.categories[ext]
        for keyword, cat in self.patterns.items():
            if keyword.lower() in filename.lower():
                return cat
        return self.categories.get('default', 'Outros')

    def _is_inactive(self, file_path):
        try:
            mtime = os.path.getmtime(file_path)
            age = time.time() - mtime
            return age > self.inactivity_hours * 3600
        except OSError:
            return False

    def organize_file(self, file_path):
        file_path = Path(file_path)
        if not file_path.is_file():
            return
        filename = file_path.name
        category = self._get_category(filename)
        dest_dir = self.temp_base / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        if dest_path.exists():
            base, ext = os.path.splitext(filename)
            timestamp = int(time.time())
            dest_path = dest_dir / f"{base}_{timestamp}{ext}"

        try:
            shutil.move(str(file_path), str(dest_path))
            self.logger.info(f"Moved inactive file: {file_path} -> {dest_path}")
        except Exception as e:
            self.logger.error(f"Failed to move {file_path}: {e}")

    def scan_and_organize(self, recursive=False):
        self.logger.info("Scanning for inactive files to organize...")
        moved_count = 0
        for directory in self.watch_dirs:
            if not directory.is_dir():
                continue

            if recursive:
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = Path(root) / file
                        if self._should_ignore(file_path):
                            continue
                        if self._is_inactive(file_path):
                            self.organize_file(file_path)
                            moved_count += 1
            else:
                for item in directory.iterdir():
                    if not item.is_file():
                        continue
                    if self._should_ignore(item):
                        continue
                    if self._is_inactive(item):
                        self.organize_file(item)
                        moved_count += 1

        self.logger.info(f"Organization scan complete. Moved {moved_count} files.")