from datetime import datetime, timedelta
import json
from config import TRASH_DIR, METADATA_FILE
import shutil
from pathlib import Path
import os


def soft_delete(ficheiro):
    if not Path(ficheiro).exists():
        return
    shutil.move(ficheiro, TRASH_DIR)

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
        json.dump(metadata, f)


def verificar_lixeira():
    with open(METADATA_FILE, 'r') as f:
        metadata = json.load(f)
    a_apagar = []

    for ficheiro in list(metadata.keys()):
        hora_entrada = datetime.strptime(metadata[ficheiro]["hora_entrada"], "%Y-%m-%dT%H:%M:%S")
        agora = datetime.now()

        if agora - hora_entrada >= timedelta(hours=24):
            os.remove(TRASH_DIR / ficheiro)
            a_apagar.append(ficheiro)

    for ficheiro in a_apagar:
        del metadata[ficheiro]

    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)
