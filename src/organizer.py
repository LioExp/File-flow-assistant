import os
import shutil
import time
from pathlib import Path

class FileOrganizer:
    def __init__(self, logger, watch_dirs, temp_base, categories, patterns, ignore_patterns, inactivity_hours):
        self.logger = logger
        self.watch_dirs = watch_dirs
        self.temp_base = temp_base
        self.categories = categories
        self.patterns = patterns
        self.ignore_patterns = ignore_patterns
        self.inactivity_hours = inactivity_hours

    def _should_ignore(self, file_path):
        """Verifica se o arquivo está em um padrão de ignorar."""
        for pattern in self.ignore_patterns:
            if pattern in file_path:
                return True
        return False

    def _get_category(self, filename):
        """Determina a categoria baseada na extensão ou palavra-chave."""
        ext = os.path.splitext(filename)[1].lower()
        # Primeiro por extensão
        if ext in self.categories:
            return self.categories[ext]
        # Depois por palavra-chave
        for keyword, cat in self.patterns.items():
            if keyword.lower() in filename.lower():
                return cat
        return self.categories.get('default', 'Outros')

    def _is_inactive(self, file_path):
        """Verifica se o arquivo está inativo há mais de N horas."""
        try:
            mtime = os.path.getmtime(file_path)
            age = time.time() - mtime
            return age > self.inactivity_hours * 3600
        except OSError:
            return False

    def organize_file(self, file_path):
        """Move um arquivo para a pasta temporária, na subpasta da categoria."""
        if not os.path.isfile(file_path):
            return
        filename = os.path.basename(file_path)
        category = self._get_category(filename)
        dest_dir = os.path.join(self.temp_base, category)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)

        # Evita sobrescrever: adiciona timestamp se já existir
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            timestamp = int(time.time())
            dest_path = os.path.join(dest_dir, f"{base}_{timestamp}{ext}")

        try:
            shutil.move(file_path, dest_path)
            self.logger.info(f"Moved inactive file: {file_path} -> {dest_path}")
        except Exception as e:
            self.logger.error(f"Failed to move {file_path}: {e}")

    def scan_and_organize(self, recursive=False):
        """Percorre os diretórios monitorados e move arquivos inativos."""
        self.logger.info("Scanning for inactive files to organize...")
        moved_count = 0
        for directory in self.watch_dirs:
            if not os.path.isdir(directory):
                continue

            if recursive:
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._should_ignore(file_path):
                            continue
                        if self._is_inactive(file_path):
                            self.organize_file(file_path)
                            moved_count += 1
            else:
                for item in os.listdir(directory):
                    file_path = os.path.join(directory, item)
                    if not os.path.isfile(file_path):
                        continue
                    if self._should_ignore(file_path):
                        continue
                    if self._is_inactive(file_path):
                        self.organize_file(file_path)
                        moved_count += 1

        self.logger.info(f"Organization scan complete. Moved {moved_count} files.")