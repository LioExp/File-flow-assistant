import datetime import datetime
import json
from config import TRASH_DIR, METADATA_FILE
import shutil
from pathlib import Path


def soft_delete(ficheiro):
    # pega o ficheiro deletado
    if not Path(ficheiro).exists():
        return
    # copia ou move pra fileflow_trash
    shutil.move(ficheiro, TRASH_DIR)

    # e registra-o no metadata.json
    if Path(METADATA_FILE).exists():
        with open(METADATA_FILE, "r") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    metadata[Path(ficheiro).name] = {
            'hora_entrada': datetime.now().isoformat(),
            'caminho_original': str(ficheiro),
            }
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata,f)
    
