import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".fileflow" / "watch_dirs.json"

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
    expanded = os.path.expanduser(path)
    if expanded not in dirs:
        dirs.append(expanded)
        save_dirs(dirs)
        return True, expanded
    return False, expanded


def remove_dir(path):
    dirs = load_dirs()
    expanded = os.path.expanduser(path)
    if expanded in dirs:
        dirs.remove(expanded)
        save_dirs(dirs)
        return True, expanded
    return False, expanded
