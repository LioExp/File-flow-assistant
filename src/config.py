import os
from pathlib import Path
from watch_config import load_dirs, FILEFLOW_HOME

__all__ = [
    'WATCH_DIRECTORIES', 'TEMP_BASE_DIR', 'TEMP_CATEGORIES',
    'WATCH_DELAY', 'WATCH_RECURSIVELY',
    'TRIGGER_MIN_FILES', 'TRIGGER_INACTIVITY_HOURS', 'TRIGGER_DESKTOP_COVERAGE',
    'MONITORED_EXTENSIONS', 'KEYWORD_PATTERNS', 'IGNORE_PATTERNS',
    'SYSTEM_TEMP_PATTERNS', 'LOG_LEVEL', 'BEGINNER_MODE',
    'TRASH_DIR', 'METADATA_FILE', 'FILEFLOW_HOME'
]

WATCH_DIRECTORIES = load_dirs()

TEMP_BASE_DIR = os.path.expanduser("~/file_flow_temp")

TEMP_CATEGORIES = {
    '.pdf': 'Docs',
    '.txt': 'Docs',
    '.docx': 'Docs',
    '.jpg': 'Imagens',
    '.jpeg': 'Imagens',
    '.png': 'Imagens',
    '.mp4': 'Videos',
    '.zip': 'Compactados',
    '.rar': 'Compactados',
    'default': 'Outros'
}

WATCH_DELAY = 5
WATCH_RECURSIVELY = False

TRIGGER_MIN_FILES = 3
TRIGGER_INACTIVITY_HOURS = 48
TRIGGER_DESKTOP_COVERAGE = 70

MONITORED_EXTENSIONS = (
    '.pdf', '.docx', '.txt',
    '.jpg', '.jpeg', '.png',
    '.mp4', '.zip', '.rar',
    '.py', '.js', '.html'
)

KEYWORD_PATTERNS = {
    'projeto': 'Projetos',
    'relatorio': 'Relatorios',
    'contrato': 'Contratos',
    'foto': 'Fotos_Pessoais',
    'screenshot': 'Capturas'
}

IGNORE_PATTERNS = [
    '.git',
    'venv',
    'node_modules',
    '__pycache__',
    '.DS_Store'
]

SYSTEM_TEMP_PATTERNS = ['~$', '.tmp', '.crdownload']

LOG_LEVEL = "DEBUG"

BEGINNER_MODE = True

TRASH_DIR = Path.home() / ".fileflow_trash"
METADATA_FILE = TRASH_DIR / "metadata.json"
