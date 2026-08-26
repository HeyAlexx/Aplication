from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from enrich_anime_metadata import (
    ANIME_PATH,
    STATE_PATH,
    anilist_candidates,
    candidate_score,
    expected_season,
    format_key,
    kitsu_candidates,
    normalize_title,
    title_season,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "outputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera un reporte de conflictos de metadatos de anime.")
    parser.add_argument("--requests-per-minute", type=int, default=30)
    return parser.parse_args()


def load_json(path: Path, fallback: object) -> object:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_titles(candidate: dict[str, object]) -> list[str]:
    return [
        str(candidate.get("title") or ""),
        str(candidate.get("alternativeTitle") or ""),
        *[str(title or "") for title in candidate.get("alternativeTitles") or []],
    ]


def explain_conflicts(record: dict[str, object], candidate: dict[str, object] | None) -> list[str]:
    if candidate is None:
        return ["No se encontró un candidato en AniList ni Kitsu."]

    reasons = []
    local_title = normalize_title(record.get("title"))
    api_titles = {normalize_title(title) for title in candidate_titles(candidate)}

    if local_title not in api_titles:
        reasons.append("El título local no coincide exactamente con los títulos o alias de la API.")

    local_format = format_key(record.get("format"))
    api_format = format_key(candidate.get("format"))
    if local_format != api_format:
        reasons.append(f"Formato distinto: local {record.get('format') or '-'} / API {candidate.get('format') or '-'}.")

    local_year = int(record.get("emissionYear") or 0)
    api_year = int(candidate.get("emissionYear") or 0)
    if local_year and api_year and local_year != api_year:
        reasons.append(f"Año distinto: local {local_year} / API {api_year}.")

    local_season = str(record.get("emissionSeason") or "").casefold()
    api_season = str(candidate.get("emissionSeason") or "").casefold()
    if local_season and api_season and local_season != api_season:
        reasons.append(
            f"Temporada de emisión distinta: local {record.get('emissionSeason')} / API {candidate.get('emissionSeason')}."
        )

    wanted_season = expected_season(record)
    api_title_seasons = {season for title in candidate_titles(candidate) if (season := title_season(title))}
    if wanted_season > 1 and wanted_season not in api_title_seasons:
        reasons.append(f"El Excel indica S{wanted_season:02d}, pero el candidato no identifica esa temporada.")

    if not reasons:
        reasons.append("La coincidencia es cercana, pero no alcanzó el umbral conservador de 0.80.")
    return reasons


def classify(record: dict[str, object], candidate: dict[str, object] | None, score: float) -> str:
    if candidate is None:
        return "Sin candidato"

    local_title = normalize_title(record.get("title"))
    api_titles = {normalize_title(title) for title in candidate_titles(candidate)}
    local_year = int(record.get("emissionYear") or 0)
    api_year = int(candidate.get("emissionYear") or 0)
    title_matches = local_title in api_titles
    year_matches = not local_year or not api_year or local_year == api_year

    if title_matches and year_matches:
        return "Conflicto probable"
    if score >= 0.65:
        return "Revisión recomendada"
    if local_year >= datetime.now().year:
        return "Estreno futuro o sin publicar"
    return "Alias o título distinto"


def best_candidate(record: dict[str, object]) -> tuple[dict[str, object] | None, float, list[str]]:
    errors = []
    candidates = []

    for provider, lookup in (("anilist", anilist_candidates), ("kitsu", kitsu_candidates)):
        try:
            candidates.extend(lookup(str(record.get("title") or "")))
        except Exception as error:  # El reporte debe continuar aunque un proveedor falle.
            errors.append(f"{provider}: {error}")

    ranked = sorted(
        ((candidate_score(record, candidate), candidate) for candidate in candidates),
        key=lambda entry: entry[0],
        reverse=True,
    )
    if not ranked:
        return None, 0.0, errors
    return ranked[0][1], ranked[0][0], errors


def markdown_table(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Revisión de conflictos de anime",
        "",
        f"Generado: {datetime.now().astimezone().isoformat()}",
        "",
        "Este reporte no modifica `anime.json`. Presenta el mejor candidato para revisión manual.",
        "",
        "| # | Clasificación | Anime local | Datos locales | Mejor candidato API | Datos API | Puntaje | Conflicto |",
        "|---:|---|---|---|---|---|---:|---|",
    ]

    for index, row in enumerate(rows, start=1):
        local = row["local"]
        candidate = row.get("candidate") or {}
        conflict = " ".join(row["conflicts"]).replace("|", "/")
        local_data = f"{local.get('emissionYear') or '-'} / {local.get('emissionSeason') or '-'} / {local.get('format') or '-'} / {local.get('activeSeason') or '-'}"
        api_data = f"{candidate.get('emissionYear') or '-'} / {candidate.get('emissionSeason') or '-'} / {candidate.get('format') or '-'} / {candidate.get('source') or '-'}"
        lines.append(
            f"| {index} | {row['classification']} | {str(local.get('title') or '').replace('|', '/')} | "
            f"{local_data} | {str(candidate.get('title') or 'Sin candidato').replace('|', '/')} | "
            f"{api_data} | {row['score']:.2f} | {conflict} |"
        )

    lines.extend([
        "",
        "## Criterio sugerido",
        "",
        "- **Conflicto probable:** título y año coinciden; normalmente se debe corregir formato o temporada local.",
        "- **Revisión recomendada:** el candidato es cercano, pero existe una diferencia relevante.",
        "- **Estreno futuro o sin publicar:** el proveedor todavía puede no tener metadatos definitivos.",
        "- **Alias o título distinto:** conviene confirmar el nombre oficial antes de aceptar.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    if not 1 <= args.requests_per_minute <= 60:
        raise SystemExit("requests-per-minute debe estar entre 1 y 60.")

    records = load_json(ANIME_PATH, [])
    state = load_json(STATE_PATH, {})
    unmatched_ids = set((state.get("unmatched") or {}).keys())
    records_by_id = {str(record.get("id") or ""): record for record in records}
    pending = [records_by_id[record_id] for record_id in unmatched_ids if record_id in records_by_id]
    pending.sort(key=lambda record: int(record.get("sourceRow") or 0))
    interval = 60 / args.requests_per_minute
    rows = []

    for index, record in enumerate(pending, start=1):
        started = time.monotonic()
        candidate, score, errors = best_candidate(record)
        row = {
            "id": record.get("id"),
            "classification": classify(record, candidate, score),
            "score": round(score, 4),
            "local": {
                key: record.get(key)
                for key in ("title", "emissionYear", "emissionSeason", "format", "activeSeason", "chapters")
            },
            "candidate": candidate,
            "conflicts": explain_conflicts(record, candidate),
            "providerErrors": errors,
        }
        rows.append(row)
        print(f"[{index}/{len(pending)}] {record.get('title')}: {row['classification']} ({score:.2f})", flush=True)
        delay = interval - (time.monotonic() - started)
        if delay > 0 and index < len(pending):
            time.sleep(delay)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "anime-conflicts-review.json"
    markdown_path = OUTPUT_DIR / "anime-conflicts-review.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_table(rows), encoding="utf-8")

    summary = {}
    for row in rows:
        summary[row["classification"]] = summary.get(row["classification"], 0) + 1
    print(json.dumps({"total": len(rows), "summary": summary, "markdown": str(markdown_path), "json": str(json_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
