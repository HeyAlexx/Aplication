"""Short cross-process locks and recoverable JSON collection commits (PHP compatible)."""
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = '.storage.lock'
JOURNAL_NAME = '.transaction.json'


@contextmanager
def file_lock(path: Path, *, timeout: float = 15):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Almacenamiento ocupado por otro proceso; reintente.')
                time.sleep(0.01)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + '.tmp-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def recover(directory: Path):
    journal = directory / JOURNAL_NAME
    if not journal.exists():
        return
    payload = json.loads(journal.read_text(encoding='utf-8'))
    if payload.get('version') != 1 or not isinstance(payload.get('files'), dict):
        raise RuntimeError('Diario de transacción inválido; no se descartará.')
    for name, records in payload['files'].items():
        if not re.fullmatch(r'[a-zA-Z0-9-]+\.json', name) or not isinstance(records, list):
            raise RuntimeError('Colección de recuperación inválida.')
        atomic_json(directory / name, records)
    journal.unlink()


@contextmanager
def storage_lock(directory: Path):
    with file_lock(directory / LOCK_NAME):
        recover(directory)
        yield


def commit_collections(directory: Path, files: dict):
    # Caller holds storage_lock. A crash after the journal is durable rolls forward.
    atomic_json(directory / JOURNAL_NAME, {'version': 1, 'files': files})
    recover(directory)
