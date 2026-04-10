import sqlite3
import os
import json
from datetime import datetime

class FileIndex:
    def __init__(self, db_path='fileflow.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    size INTEGER,
                    hash TEXT,
                    last_modified TEXT,
                    first_seen TEXT
                )
            ''')

    def add_or_update(self, path, size, file_hash, last_modified):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO files (path, size, hash, last_modified, first_seen)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    size=excluded.size,
                    hash=excluded.hash,
                    last_modified=excluded.last_modified
            ''', (path, size, file_hash, last_modified, datetime.now().isoformat()))

    def remove(self, path):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM files WHERE path = ?', (path,))

    def get_all_hashes(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT hash, path FROM files')
            return {row[0]: row[1] for row in cursor.fetchall()}

    def path_exists(self, path):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT 1 FROM files WHERE path = ?', (path,))
            return cursor.fetchone() is not None
        
    def get_file_info(self, path):
        """Retorna as informações de um arquivo pelo caminho, ou None se não existir."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT size, hash, last_modified FROM files WHERE path = ?', (path,))
            row = cursor.fetchone()
            if row:
                return {'size': row[0], 'hash': row[1], 'last_modified': row[2]}
        return None    

