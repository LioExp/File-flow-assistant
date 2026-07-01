import sqlite3
import threading
from datetime import datetime

__all__ = ['FileIndex']


class FileIndex:
    def __init__(self, db_path='fileflow.db'):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=5000')
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                size INTEGER,
                hash TEXT,
                last_modified REAL,
                first_seen TEXT
            )
        ''')
        conn.commit()

    def add_or_update(self, path, size, file_hash, last_modified):
        conn = self._get_conn()
        conn.execute('''
            INSERT INTO files (path, size, hash, last_modified, first_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size,
                hash=excluded.hash,
                last_modified=excluded.last_modified
        ''', (path, size, file_hash, last_modified, datetime.now().isoformat()))
        conn.commit()

    def remove(self, path):
        conn = self._get_conn()
        conn.execute('DELETE FROM files WHERE path = ?', (path,))
        conn.commit()

    def get_all_hashes(self):
        conn = self._get_conn()
        cursor = conn.execute('SELECT hash, path FROM files')
        return {row[0]: row[1] for row in cursor.fetchall()}

    def path_exists(self, path):
        conn = self._get_conn()
        cursor = conn.execute('SELECT 1 FROM files WHERE path = ?', (path,))
        return cursor.fetchone() is not None

    def get_file_info(self, path):
        conn = self._get_conn()
        cursor = conn.execute('SELECT size, hash, last_modified FROM files WHERE path = ?', (path,))
        row = cursor.fetchone()
        if row:
            return {'size': row[0], 'hash': row[1], 'last_modified': row[2]}
        return None
