import os
import json
import shutil
import tempfile
import sqlite3
from pathlib import Path

from config import TRASH_DIR, METADATA_FILE

__all__ = [
    'get_status_data', 'db_info', 'db_reset',
    'trash_list', 'trash_recover', 'trash_clean', 'format_size'
]
from database import FileIndex


def get_status_data():
    from config import (
        WATCH_DIRECTORIES, TEMP_BASE_DIR,
        TRIGGER_INACTIVITY_HOURS, WATCH_DELAY, WATCH_RECURSIVELY
    )
    from rules import load_rules

    index = FileIndex()
    file_count = None
    try:
        with sqlite3.connect(index.db_path) as conn:
            file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    except Exception:
        pass

    return {
        'watch_directories': WATCH_DIRECTORIES,
        'temp_base': TEMP_BASE_DIR,
        'inactivity_hours': TRIGGER_INACTIVITY_HOURS,
        'watch_delay': WATCH_DELAY,
        'recursive': WATCH_RECURSIVELY,
        'indexed_files': file_count,
        'rules_count': len(load_rules()),
    }


def db_info():
    index = FileIndex()
    try:
        with sqlite3.connect(index.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        return {'path': index.db_path, 'count': count, 'error': None}
    except Exception as e:
        return {'path': index.db_path, 'count': None, 'error': str(e)}


def db_reset():
    index = FileIndex()
    if os.path.exists(index.db_path):
        os.remove(index.db_path)
    FileIndex(index.db_path)._init_db()


def _load_metadata():
    if not METADATA_FILE.exists():
        return None
    try:
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(metadata, dict):
        return None
    return metadata


def _save_metadata(metadata):
    fd, tmp_path = tempfile.mkstemp(dir=TRASH_DIR, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(metadata, f, indent=2)
        shutil.move(str(tmp_path), str(METADATA_FILE))
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def trash_list():
    metadata = _load_metadata()
    if metadata is None:
        return None
    items = []
    for trash_name, info in metadata.items():
        if isinstance(info, dict) and 'original_path' in info:
            items.append({
                'trash_name': trash_name,
                'original_path': info.get('original_path', '?'),
                'deleted_at': info.get('deleted_at', '?'),
            })
    return items


def trash_recover(identifier):
    metadata = _load_metadata()
    if metadata is None:
        return None, "Trash is empty or corrupted"

    keys = list(metadata.keys())
    trash_name = None

    if identifier in metadata:
        trash_name = identifier
    elif identifier.isdigit():
        idx = int(identifier) - 1
        if 0 <= idx < len(keys):
            trash_name = keys[idx]

    if not trash_name or trash_name not in metadata:
        return None, f"'{identifier}' not found in trash"

    info = metadata[trash_name]
    if not isinstance(info, dict) or 'original_path' not in info:
        return None, f"Corrupted metadata for '{trash_name}'"

    original_path = Path(info['original_path'])
    original_path.parent.mkdir(parents=True, exist_ok=True)

    src = TRASH_DIR / trash_name
    if not src.exists():
        return None, f"File not found on disk: {src}"

    dest = original_path
    if dest.exists():
        base, ext = os.path.splitext(dest.name)
        dest = dest.parent / f"{base}_recovered_{int(os.path.getmtime(src))}{ext}"

    shutil.move(str(src), str(dest))

    del metadata[trash_name]
    _save_metadata(metadata)

    return dest, None


def trash_clean():
    from trash import clean_expired
    return clean_expired()


def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
