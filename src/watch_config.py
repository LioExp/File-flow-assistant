import json
import os
from pathlib import Path

__all__ = ['FILEFLOW_HOME', 'load_dirs', 'save_dirs', 'add_dir', 'remove_dir']

FILEFLOW_HOME = Path.home() / ".fileflow"
CONFIG_PATH = FILEFLOW_HOME / "watch_dirs.json"

DEFAULT_DIRS = [
    os.path.expanduser("~/Desktop"),
]


def _ensure_dir():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_dirs():
    _ensure_dir()
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        return data.get("directories", [])
    return list(DEFAULT_DIRS)


def save_dirs(directories):
    _ensure_dir()
    with open(CONFIG_PATH, "w") as f:
        json.dump({"directories": directories}, f, indent=2)


def add_dir(path):
    dirs = load_dirs()
    expanded = str(Path(path).expanduser().resolve())
    if not os.path.isdir(expanded):
        return False, expanded, "Path is not a directory or does not exist"
    if expanded in dirs:
        return False, expanded, "Already monitored"
    dirs.append(expanded)
    save_dirs(dirs)
    return True, expanded, None


def remove_dir(path):
    dirs = load_dirs()
    expanded = str(Path(path).expanduser().resolve())
    if expanded in dirs:
        dirs.remove(expanded)
        save_dirs(dirs)
        return True, expanded, None
    return False, expanded, "Not found"
