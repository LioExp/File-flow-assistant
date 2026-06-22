from datetime import datetime, timedelta
import json
from config import TRASH_DIR, METADATA_FILE
import shutil
from pathlib import Path
import os
import sys
import time


def soft_delete(ficheiro):
    if not Path(ficheiro).exists():
        return

    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    dest = TRASH_DIR / Path(ficheiro).name

    if sys.platform == 'win32' and dest.exists():
        base, ext = os.path.splitext(dest.name)
        dest = TRASH_DIR / f"{base}_{int(time.time())}{ext}"

    shutil.move(str(ficheiro), str(dest))

    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    metadata[Path(ficheiro).name] = {
        'hora_entrada': datetime.now().isoformat(),
        'caminho_original': str(ficheiro),
    }
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)


def verificar_lixeira():
    if not METADATA_FILE.exists():
        return

    with open(METADATA_FILE, 'r') as f:
        metadata = json.load(f)

    a_apagar = []

    for ficheiro in list(metadata.keys()):
        hora_entrada = datetime.fromisoformat(metadata[ficheiro]["hora_entrada"])
        agora = datetime.now()

        if agora - hora_entrada >= timedelta(days=30):
            target = TRASH_DIR / ficheiro
            if target.exists():
                try:
                    os.remove(str(target))
                except OSError:
                    if sys.platform == 'win32':
                        time.sleep(0.1)
                        try:
                            os.remove(str(target))
                        except OSError:
                            continue
            a_apagar.append(ficheiro)

    for ficheiro in a_apagar:
        del metadata[ficheiro]

    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
