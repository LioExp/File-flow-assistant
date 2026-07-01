import os
import shutil
import time
from pathlib import Path

__all__ = ['FileOrganizer']


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

    def _resolve_dest(self, source_path):
        category = self._get_category(source_path.name)
        dest_dir = self.temp_base / category
        dest = dest_dir / source_path.name
        if dest.exists():
            base, ext = os.path.splitext(source_path.name)
            dest = dest_dir / f"{base}_{int(time.time())}{ext}"
        return dest, category

    def preview(self, recursive=False):
        results = []
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
                            dest, category = self._resolve_dest(file_path)
                            results.append({
                                'source': file_path,
                                'dest': dest,
                                'category': category,
                                'size': file_path.stat().st_size,
                            })
            else:
                for item in directory.iterdir():
                    if not item.is_file():
                        continue
                    if self._should_ignore(item):
                        continue
                    if self._is_inactive(item):
                        dest, category = self._resolve_dest(item)
                        results.append({
                            'source': item,
                            'dest': dest,
                            'category': category,
                            'size': item.stat().st_size,
                        })
        return results

    def organize_file(self, file_path):
        file_path = Path(file_path)
        if not file_path.is_file():
            return False

        dest, _ = self._resolve_dest(file_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(file_path), str(dest))
            self.logger.info(f"Moved: {file_path} -> {dest}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move {file_path}: {e}")
            return False

    def organize_selected(self, file_paths):
        moved = 0
        for fp in file_paths:
            if self.organize_file(fp):
                moved += 1
        return moved
