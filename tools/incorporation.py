"""Immutable first incorporation for Sheet batches; never the last sync time."""
from datetime import datetime
import hashlib

FIELDS = ('incorporatedAt', 'sheetImportBatchId', 'sheetImportRow', 'incorporationDateBasis')


def batch_id(timestamp: str, basis: str = 'initial-sheet-sync') -> str:
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        raise ValueError('La fecha del lote debe incluir zona horaria.')
    return 'sheet-' + hashlib.sha256((basis + ':' + timestamp).encode()).hexdigest()[:24]


def stamp(record: dict, row: int, timestamp: str, basis: str = 'initial-sheet-sync') -> bool:
    if record.get('sheetImportBatchId'):
        return False
    if not isinstance(row, int) or row < 2:
        raise ValueError('La incorporación de Sheets requiere una fila válida.')
    identifier = batch_id(timestamp, basis)
    record.update({'incorporatedAt': timestamp, 'sheetImportBatchId': identifier,
                   'sheetImportRow': row, 'incorporationDateBasis': basis})
    return True
