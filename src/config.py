import os
# ================================
# MAIN PATHS
# ================================
# Path that app will monitor
WATCH_DIRECTORIES = [
    os.path.expanduser("~/Downloads"),     
    os.path.expanduser("~/Desktop"),       
    os.path.expanduser("~/Documents"),    
]

# temporary paths where files will be move to choice
TEMP_BASE_DIR = os.path.expanduser("~/file_flow_temp")

# Subpastas automáticas dentro da temp (por categoria)
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
    'default': 'Outros'  # Para extensões desconhecidas
}

# ================================
# MONITORATION
# ================================
# Delay between checkin (em segundos)
WATCH_DELAY = 5  

# to Monitor sub paths too?
WATCH_RECURSIVELY = False  # pra evitar complexidade ainda

# Monitorar criação de pastas também (útil no futuro)?
WATCH_DIRECTORIES_EVENTS = False

# ================================
# TRIGGERS DE ATIVAÇÃO (Fase 1)
# ================================
# Ativar organização automática se...
TRIGGER_MIN_FILES = 3  # Mais de X arquivos novos na pasta
TRIGGER_INACTIVITY_HOURS = 48  # Arquivo não tocado há X horas
TRIGGER_DESKTOP_COVERAGE = 70  # % da área de trabalho coberta (futura implementação)

# Agendamento automático (ex: toda segunda às 9h) — futuro
SCHEDULED_ORGANIZE = None 

# ================================
# EXTENSION AND STANDARDS
# ================================
# Extensions that app will consider
MONITORED_EXTENSIONS = (
    '.pdf', '.docx', '.txt',
    '.jpg', '.jpeg', '.png',
    '.mp4', '.zip', '.rar',
    '.py', '.js', '.html'  # Útil pra devs como você
)

# Palavras-chave pra detecção inteligente (ex: nome do arquivo)
KEYWORD_PATTERNS = {
    'projeto': 'Projetos',
    'relatorio': 'Relatorios',
    'contrato': 'Contratos',
    'foto': 'Fotos_Pessoais',
    'screenshot': 'Capturas'
}

# ================================
# EXECUTION AND SECURITY
# ================================

# Paths or standard to ignore completely (ex: dev projets Paths )
IGNORE_PATTERNS = [
    '.git',
    'venv',
    'node_modules',
    '__pycache__',
    '.DS_Store'
]

# temporary Files from system for dont touching
SYSTEM_TEMP_PATTERNS = ['~$', '.tmp', '.crdownload']

# ================================
# another
# ================================
# Log of app (to debug)
LOG_LEVEL = "DEBUG"  #'DEBUG' to see all, 'INFO' no


# Beginner mode more notification and lass automation
BEGINNER_MODE = True


# Cores ANSI para cada tipo de evento
RESET = '\033[0m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'
# ... outras cores se necessário