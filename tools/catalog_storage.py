"""Resolve deployment data independently of the Git branch."""
import json
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.environ.get("ALTOIDSS_STORAGE_CONFIG") or
                   PROJECT_DIR.parent / "catalog-storage.local.json")
if os.environ.get("ALTOIDSS_STORAGE_CONFIG") and not CONFIG_PATH.is_file():
    raise RuntimeError("No existe el descriptor central solicitado.")
SETTINGS = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else None
if SETTINGS:
    for key in ("catalogDir", "syncStateDir"):
        if not SETTINGS.get(key) or not Path(SETTINGS[key]).is_dir():
            raise RuntimeError(f"Almacenamiento central no disponible: {key}")

CATALOG_DIR = Path(SETTINGS["catalogDir"]) if SETTINGS else PROJECT_DIR / "data"
SYNC_STATE_DIR = Path(SETTINGS["syncStateDir"]) if SETTINGS else PROJECT_DIR / "runtime" / "anime-sync"


def guard_legacy_write() -> None:
    """Old bulk utilities bypass approval/writeback; never let them replace shared data."""
    if SETTINGS:
        raise SystemExit("Esta utilidad masiva no escribe en el catálogo central. Use el administrador o anime_sync_pipeline.py para conservar revisiones y cola de Sheets.")
