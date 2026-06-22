import os
import sys
from pathlib import Path

if sys.platform == 'win32':
    os.system('')

WATCH_DIRECTORIES = [
    os.path.expanduser("~/Desktop"),
]

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
WATCH_DIRECTORIES_EVENTS = False

TRIGGER_MIN_FILES = 3
TRIGGER_INACTIVITY_HOURS = 48
TRIGGER_DESKTOP_COVERAGE = 70

SCHEDULED_ORGANIZE = None

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

GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'

TRASH_DIR = Path.home() / ".fileflow_trash"
METADATA_FILE = TRASH_DIR / "metadata.json"

