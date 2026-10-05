from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from enrich_anime_metadata import (
    anilist_candidates,
    candidate_score,
    enrich_record,
    jikan_candidates,
    kitsu_candidates,
    normalize_title,
    normalized_format,
)
from sync_anime_workbook import (
    ANIME_PATH,
    MANAGED_FIELDS,
    build_index,
    make_new_record,
    raw_row,
    read_catalog,
)
from google_sheets_writeback import read_rows, update_rows


PROJECT_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = PROJECT_DIR / "runtime" / "anime-sync"
STATE_PATH = STATE_DIR / "state.json"
REPORT_PATH = STATE_DIR / "last-report.json"
CONFLICTS_PATH = STATE_DIR / "pending-review.json"
REVIEW_DATA_PATH = PROJECT_DIR / "data" / "anime-revisiones.json"
WRITEBACK_QUEUE_PATH = PROJECT_DIR / "data" / "anime-sheet-writeback.json"
PREVIOUS_JSON_PATH = STATE_DIR / "anime.previous.json"
LOCK_PATH = STATE_DIR / "watcher.pid"
DEFAULT_CONFIG = PROJECT_DIR / "config" / "anime-sync.json"
METADATA_FIELDS = {"title", "format", "emissionYear", "emissionSeason", "activeSeason", "chapters", "seasonsCount"}
ALLOWED_FORMATS = {"Serie", "Película", "OVA", "ONA", "Especial"}
ALLOWED_STATUSES = {"Emisión", "Finalizado", "Pausado", "Próximamente", "Cancelado", "Pendiente"}
ALLOWED_VIEWING = {"Visto", "No Visto", "Por Ver", "Ignorado"}
SEASON_SUFFIX = re.compile(
    r"(?:\s+season\s*(\d+)|\s+s(\d+)|\s+(\d+)(?:st|nd|rd|th)(?:\s+season)?|\s+(\d+)|\s+ni)\s*$",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sincroniza, valida y enriquece el catálogo de anime de Altoidss.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--url")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--requests-per-minute", type=int, default=30)
    return parser.parse_args()


def load_json(path: Path, fallback: object) -> object:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def row_payload(item: dict[str, object]) -> dict[str, object]:
    return {key: item.get(key) for key in ("sourceCode", "title", "productionStatus", "format", "chapters", "seasonsCount", "activeSeason", "viewingStatus", "emissionYear", "emissionSeason")}


def rows_hash(items: list[dict[str, object]]) -> str:
    payload = json.dumps([row_payload(item) for item in items], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def config_source(args: argparse.Namespace) -> tuple[Path | None, str]:
    config = load_json(args.config, {})
    workbook = args.workbook or (Path(str(config.get("workbook"))) if config.get("workbook") else None)
    url = args.url or str(config.get("googleExportUrl") or "")
    return workbook, url


def download_workbook(url: str) -> Path:
    request = Request(url, headers={"User-Agent": "Altoidss-sync/1.0"})
    try:
        with urlopen(request, timeout=45) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read()
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"No se pudo descargar la hoja de Google: {error}") from error
    if not payload.startswith(b"PK"):
        detail = "La hoja requiere iniciar sesión" if "text/html" in content_type else "Google no devolvió un XLSX"
        raise RuntimeError(f"{detail}. Publíquela para lectura o configure OAuth antes de activar el modo automático.")
    handle = tempfile.NamedTemporaryFile(prefix="altoidss-anime-", suffix=".xlsx", delete=False)
    handle.write(payload)
    handle.close()
    return Path(handle.name)


def validate_source(items: list[dict[str, object]]) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    codes: set[str] = set()
    current_year = datetime.now().year
    for item in items:
        code = str(item.get("sourceCode") or "")
        title = str(item.get("title") or "")
        row = item.get("row")
        errors = []
        if not code or code in codes:
            errors.append("Código vacío o duplicado")
        if not title:
            errors.append("Título vacío")
        codes.add(code)
        if item.get("format") not in ALLOWED_FORMATS:
            errors.append(f"Formato no reconocido: {item.get('format')}")
        if item.get("productionStatus") not in ALLOWED_STATUSES:
            errors.append(f"Estado de emisión no reconocido: {item.get('productionStatus')}")
        if item.get("viewingStatus") not in ALLOWED_VIEWING:
            errors.append(f"Estado de visualización no reconocido: {item.get('viewingStatus')}")
        year = int(item.get("emissionYear") or 0)
        if year and not 1900 <= year <= current_year + 8:
            errors.append(f"Año fuera de rango: {year}")
        if int(item.get("chapters") or 0) < 0 or int(item.get("seasonsCount") or 0) < 0:
            errors.append("Capítulos y temporadas no pueden ser negativos")
        season = str(item.get("activeSeason") or "")
        if season and not re.fullmatch(r"S\d{2}", season, re.IGNORECASE):
            errors.append(f"Código de temporada inválido: {season}")
        if season.upper() == "S00" and item.get("format") == "Serie" and int(item.get("chapters") or 0) != 1:
            errors.append("S00 solo corresponde a película o contenido de un capítulo")
        if errors:
            issues.append({"sourceCode": code, "row": row, "title": title, "errors": errors})
    return issues


def title_identity(value: object) -> tuple[str, int | None]:
    title = normalize_title(value)
    match = SEASON_SUFFIX.search(title)
    if not match:
        return title, None
    season = next((int(value) for value in match.groups() if value), 2 if title.endswith(" ni") else None)
    return title[: match.start()].strip(), season


def candidate_titles(candidate: dict[str, object]) -> list[str]:
    return [
        str(candidate.get("title") or ""),
        str(candidate.get("alternativeTitle") or ""),
        *[str(value or "") for value in candidate.get("alternativeTitles") or []],
    ]


def names_match(local_title: str, candidate: dict[str, object]) -> bool:
    local_base, local_season = title_identity(local_title)
    for title in candidate_titles(candidate):
        candidate_base, candidate_season = title_identity(title)
        if not candidate_base:
            continue
        same_base = local_base == candidate_base
        similar_base = candidate_score({"title": local_base, "format": "Serie"}, {"title": candidate_base, "format": "Serie"}) >= 0.92
        season_ok = local_season is None or candidate_season is None or local_season == candidate_season
        if (same_base or similar_base) and season_ok:
            return True
    return False


def best_candidate(record: dict[str, object], rpm: int) -> tuple[dict[str, object] | None, float, list[str]]:
    candidates: list[dict[str, object]] = []
    provider_errors = []
    for name, lookup in (("AniList", anilist_candidates), ("Jikan", jikan_candidates), ("Kitsu", kitsu_candidates)):
        started = time.monotonic()
        try:
            candidates.extend(lookup(str(record.get("title") or "")))
        except Exception as error:
            provider_errors.append(f"{name}: {error}")
        elapsed = time.monotonic() - started
        time.sleep(max(0, (60 / max(1, rpm)) - elapsed))
    ranked = sorted(((candidate_score(record, candidate), candidate) for candidate in candidates), reverse=True, key=lambda pair: pair[0])
    return (ranked[0][1], ranked[0][0], provider_errors) if ranked else (None, 0.0, provider_errors)


def apply_verified_metadata(record: dict[str, object], candidate: dict[str, object], score: float) -> None:
    original_title = str(record.get("title") or "")
    enrich_record(record, candidate, score)
    romaji_title = str(candidate.get("title") or "").strip()
    alternatives = [original_title, *candidate_titles(candidate)]
    record["title"] = romaji_title or original_title
    record["alternativeTitles"] = list(dict.fromkeys(value for value in alternatives if value and value != record["title"]))
    if int(candidate.get("chapters") or 0) > 0:
        record["chapters"] = int(candidate["chapters"])
    record["format"] = normalized_format(candidate.get("format") or record.get("format"))
    if candidate.get("productionStatus"):
        record["productionStatus"] = candidate["productionStatus"]
    if int(candidate.get("emissionYear") or 0) > 0:
        record["emissionYear"] = int(candidate["emissionYear"])
        record["year"] = str(candidate["emissionYear"])
    if candidate.get("emissionSeason"):
        record["emissionSeason"] = candidate["emissionSeason"]
    record["tags"] = [record.get("format", ""), record.get("viewingStatus", ""), record.get("productionStatus", "")]
    record["metadataVerified"] = True
    record["metadataNeedsReview"] = False


def review_entry(
    item: dict[str, object],
    record: dict[str, object] | None,
    candidate: dict[str, object] | None,
    status: str,
    differences: list[str],
    score: float = 0.0,
    provider_errors: list[str] | None = None,
) -> dict[str, object]:
    api_version = None
    if candidate:
        api_version = {
            **candidate,
            "title": candidate.get("title") or "",
            "alternativeTitles": list(dict.fromkeys(filter(None, [
                candidate.get("alternativeTitle"),
                *(candidate.get("alternativeTitles") or []),
            ]))),
            "format": normalized_format(candidate.get("format")),
            "externalTitle": candidate.get("title") or "",
            "metadataProvider": candidate.get("source") or "external",
            "metadataMatchScore": round(score, 4),
        }
    return {
        "id": f"anime-review-{item.get('sourceCode')}",
        "contentId": (record or {}).get("id", ""),
        "sourceCode": item.get("sourceCode", ""),
        "title": item.get("title", ""),
        "status": status,
        "differences": differences,
        "matchScore": round(score, 4),
        "original": row_payload(item),
        "apiVersion": api_version,
        "providerErrors": provider_errors or [],
        "detectedAt": datetime.now().astimezone().isoformat(),
    }


def merge_reviews(generated: list[dict[str, object]]) -> list[dict[str, object]]:
    existing = load_json(REVIEW_DATA_PATH, [])
    existing_by_id = {str(item.get("id") or ""): item for item in existing if isinstance(item, dict)}
    merged = []
    generated_ids = set()
    for item in generated:
        review_id = str(item.get("id") or "")
        generated_ids.add(review_id)
        previous = existing_by_id.get(review_id)
        if previous and previous.get("original") == item.get("original") and previous.get("status") in {"Aprobado", "Rechazado"}:
            preserved = (
                "status", "resolutionType", "finalVersion", "reviewNotes", "reviewedAt", "reviewedBy"
            )
            item.update({key: previous[key] for key in preserved if key in previous})
        merged.append(item)
    # A pending item that is absent from this run was resolved at the source
    # (for example, a duplicate spreadsheet row was removed). Do not keep it
    # visible forever. Decisions remain as audit history.
    merged.extend(
        item for item in existing
        if str(item.get("id") or "") not in generated_ids
        and item.get("status") in {"Aprobado", "Rechazado"}
    )
    return merged


def flush_sheet_writebacks(config_path: Path) -> int:
    """Write approved rows back to Sheets and retain only failed queue entries."""
    config = load_json(config_path, {})
    settings = config.get("googleSheets") if isinstance(config, dict) else {}
    if not isinstance(settings, dict) or not settings.get("writeBackEnabled"):
        return 0
    queued = load_json(WRITEBACK_QUEUE_PATH, [])
    if not isinstance(queued, list):
        raise RuntimeError("anime-sheet-writeback.json no contiene una lista válida.")
    if not queued:
        return 0
    written = update_rows(config_path, queued)
    if written != len(queued):
        raise RuntimeError("Google Sheets no confirmó todas las actualizaciones en cola.")
    state = load_json(STATE_PATH, {})
    rows = state.get("rows") if isinstance(state, dict) else None
    if isinstance(rows, list):
        by_code = {str(row.get("sourceCode") or ""): row for row in rows if isinstance(row, dict)}
        season_by_quarter = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Fall"}
        for update in queued:
            values = update["values"]
            code = str(update["sourceCode"])
            by_code[code] = {
                "sourceCode": code,
                "title": values[1],
                "productionStatus": "Emisión" if values[2] == "Emision" else values[2],
                "format": "Película" if values[3] == "Movie" else values[3],
                "chapters": int(values[4] or 0),
                "seasonsCount": int(values[5] or 0),
                "activeSeason": values[6],
                "viewingStatus": "No Visto" if values[7] == "No visto" else values[7],
                "emissionYear": int(values[8] or 0) or None,
                "emissionSeason": season_by_quarter.get(int(values[9] or 0), ""),
            }
        state["rows"] = list(by_code.values())
        write_json_atomic(STATE_PATH, state)
    write_json_atomic(WRITEBACK_QUEUE_PATH, [])
    return written


def read_live_google_catalog(config_path: Path) -> list[dict[str, object]]:
    config = load_json(config_path, {})
    settings = config.get("googleSheets") if isinstance(config, dict) else {}
    if not isinstance(settings, dict):
        raise RuntimeError("Falta la configuración de Google Sheets.")
    sheet_name = str(settings.get("sheetName") or "Catalogo")
    rows = read_rows(config_path, f"{sheet_name}!A2:J")
    catalog = []
    for row_number, row in enumerate(rows, start=2):
        item = raw_row(row_number, tuple(row))
        if item["sourceCode"] and item["title"]:
            catalog.append(item)
    return catalog


def process_once(args: argparse.Namespace) -> dict[str, object]:
    workbook, url = config_source(args)
    written_back = flush_sheet_writebacks(args.config)
    config = load_json(args.config, {})
    settings = config.get("googleSheets") if isinstance(config, dict) else {}
    if isinstance(settings, dict) and settings.get("writeBackEnabled"):
        incoming = read_live_google_catalog(args.config)
    else:
        downloaded: Path | None = None
        if url:
            downloaded = download_workbook(url)
            workbook = downloaded
        if workbook is None or not workbook.exists():
            raise RuntimeError("No se configuró un archivo Excel ni una URL exportable de Google Sheets.")
        try:
            incoming = read_catalog(workbook)
        finally:
            if downloaded:
                downloaded.unlink(missing_ok=True)

    source_hash = rows_hash(incoming)
    state = load_json(STATE_PATH, {})
    if args.initialize:
        initialized = {
            "sourceHash": source_hash,
            "rows": [row_payload(item) for item in incoming],
            "lastSyncAt": datetime.now().astimezone().isoformat(),
        }
        write_json_atomic(STATE_PATH, initialized)
        report = {"status": "initialized", "totalSource": len(incoming), "timestamp": initialized["lastSyncAt"]}
        write_json_atomic(REPORT_PATH, report)
        return report
    if state.get("sourceHash") == source_hash:
        return {"status": "unchanged", "totalSource": len(incoming), "writeBackCount": written_back, "timestamp": datetime.now().astimezone().isoformat()}

    changed_codes = {
        str(item.get("sourceCode") or "")
        for item in incoming
        if previous_rows.get(str(item.get("sourceCode") or "")) != row_payload(item)
    } if (previous_rows := {str(row.get("sourceCode") or ""): row for row in state.get("rows", [])}) else {
        str(item.get("sourceCode") or "") for item in incoming
    }
    structural_issues = [
        issue for issue in validate_source(incoming)
        if str(issue.get("sourceCode") or "") in changed_codes
    ]
    invalid_codes = {str(issue["sourceCode"]) for issue in structural_issues}
    issues_by_code = {str(issue["sourceCode"]): issue for issue in structural_issues}
    records = load_json(ANIME_PATH, [])
    if not isinstance(records, list):
        raise RuntimeError("anime.json no contiene una lista válida.")
    records_by_code, records_by_title = build_index(records)
    approved = []
    conflicts = []

    for item in incoming:
        code = str(item.get("sourceCode") or "")
        current_row = row_payload(item)
        if previous_rows.get(code) == current_row:
            continue
        matches = records_by_code.get(code, [])
        if not matches:
            matches = records_by_title.get(str(item.get("title") or "").casefold(), [])
        record = copy.deepcopy(matches[0]) if len(matches) == 1 else make_new_record(item, datetime.now().astimezone().isoformat())
        is_new = not matches
        if code in invalid_codes:
            conflicts.append(review_entry(
                item,
                record,
                None,
                "Pendiente",
                list(issues_by_code[code].get("errors") or []),
            ))
            continue
        previous_row = previous_rows.get(code, {})
        changed_fields = {
            key for key in MANAGED_FIELDS.values()
            if is_new or previous_row.get(key) != item.get(key)
        }
        for key in changed_fields:
            record[key] = item.get(key)
        record["year"] = str(record.get("emissionYear") or "")
        record["tags"] = [record.get("format", ""), record.get("viewingStatus", ""), record.get("productionStatus", "")]

        needs_external_check = is_new or bool(changed_fields & METADATA_FIELDS) or not record.get("metadataVerified")
        if needs_external_check:
            candidate, score, provider_errors = best_candidate(record, args.requests_per_minute)
            if candidate is None:
                conflicts.append(review_entry(item, record, None, "Pendiente", ["Sin candidato en las APIs"], provider_errors=provider_errors))
                continue
            name_ok = names_match(str(item.get("title") or ""), candidate)
            local_year = int(item.get("emissionYear") or 0)
            api_year = int(candidate.get("emissionYear") or 0)
            year_ok = not local_year or not api_year or local_year == api_year
            differences = []
            if not name_ok:
                differences.append("nombre")
            if not year_ok:
                differences.append(f"año ({local_year}/{api_year})")
            if not name_ok and not year_ok:
                conflicts.append(review_entry(item, record, candidate, "Rechazado automático", differences, score, provider_errors))
                continue
            if differences or score < 0.8:
                conflicts.append(review_entry(item, record, candidate, "Pendiente", differences or ["Coincidencia insuficiente"], score, provider_errors))
                continue
            apply_verified_metadata(record, candidate, score)

        if is_new:
            records.append(record)
            records_by_code[code].append(record)
        else:
            matches[0].clear()
            matches[0].update(record)
        approved.append({"sourceCode": code, "title": record.get("title"), "new": is_new, "fields": sorted(changed_fields)})

    report = {
        "status": "ready" if args.apply else "preview",
        "sourceHash": source_hash,
        "sourceRows": len(incoming),
        "approved": approved,
        "approvedCount": len(approved),
        "pendingReviewCount": len(conflicts),
        "writeBackCount": written_back,
        "timestamp": datetime.now().astimezone().isoformat(),
    }
    write_json_atomic(REPORT_PATH, report)
    write_json_atomic(CONFLICTS_PATH, conflicts)
    if args.apply:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if ANIME_PATH.exists():
            shutil.copy2(ANIME_PATH, PREVIOUS_JSON_PATH)
        write_json_atomic(ANIME_PATH, records)
        write_json_atomic(REVIEW_DATA_PATH, merge_reviews(conflicts))
        write_json_atomic(STATE_PATH, {"sourceHash": source_hash, "rows": [row_payload(item) for item in incoming], "lastSyncAt": report["timestamp"]})
        report["status"] = "applied"
        write_json_atomic(REPORT_PATH, report)
    return report


def main() -> None:
    args = parse_args()
    if args.interval < 60:
        raise SystemExit("El intervalo automático mínimo es de 60 segundos.")
    if args.watch:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if LOCK_PATH.exists():
            try:
                os.kill(int(LOCK_PATH.read_text(encoding="ascii").strip()), 0)
                raise SystemExit("Ya existe un monitor de sincronización de anime en ejecución.")
            except (OSError, ValueError):
                LOCK_PATH.unlink(missing_ok=True)
        LOCK_PATH.write_text(str(os.getpid()), encoding="ascii")
    try:
        while True:
            try:
                print(json.dumps(process_once(args), ensure_ascii=False), flush=True)
            except RuntimeError as error:
                print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False), file=sys.stderr, flush=True)
                if not args.watch:
                    raise SystemExit(1) from error
            if not args.watch:
                break
            time.sleep(args.interval)
    finally:
        if args.watch and LOCK_PATH.exists() and LOCK_PATH.read_text(encoding="ascii").strip() == str(os.getpid()):
            LOCK_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
