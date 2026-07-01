from datetime import datetime, timedelta
import json
import os
import shutil
import tempfile
from pathlib import Path
from config import TRASH_DIR, METADATA_FILE

__all__ = ['soft_delete', 'clean_expired']


def _trash_name(original_path):
    p = Path(original_path)
    unique = f"{p.stem}_{abs(hash(str(p.parent))) & 0xFFFFFF:06x}{p.suffix}"
    return unique


def soft_delete(file_path):
    if not Path(file_path).exists():
        return

    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    name = _trash_name(file_path)
    dest = TRASH_DIR / name

    dest_counter = 1
    while dest.exists():
        stem = Path(name).stem
        suffix = Path(name).suffix
        dest = TRASH_DIR / f"{stem}_{dest_counter}{suffix}"
        dest_counter += 1

    shutil.move(str(file_path), str(dest))

    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    metadata[name] = {
        'deleted_at': datetime.now().isoformat(),
        'original_path': str(file_path),
    }

    fd, tmp_path = tempfile.mkstemp(dir=TRASH_DIR, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(metadata, f, indent=2)
        shutil.move(str(tmp_path), str(METADATA_FILE))
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def clean_expired():
    if not METADATA_FILE.exists():
        return 0

    with open(METADATA_FILE, 'r') as f:
        metadata = json.load(f)

    removed = []

    for name in list(metadata.keys()):
        deleted_at = datetime.fromisoformat(metadata[name]["deleted_at"])
        now = datetime.now()

        if now - deleted_at >= timedelta(days=30):
            target = TRASH_DIR / name
            if target.exists():
                try:
                    os.remove(str(target))
                except OSError:
                    pass
            removed.append(name)

    for name in removed:
        del metadata[name]

    if removed:
        fd, tmp_path = tempfile.mkstemp(dir=TRASH_DIR, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(metadata, f, indent=2)
            shutil.move(str(tmp_path), str(METADATA_FILE))
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    return len(removed)
