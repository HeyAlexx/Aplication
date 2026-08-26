#!/usr/bin/env python3
"""Apply the approved conflict-review decisions to data/anime.json."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]
ANIME_PATH = PROJECT_DIR / "data" / "anime.json"
REPORT_PATH = PROJECT_DIR / "outputs" / "anime-conflicts-review.json"
DECISIONS_PATH = (
    PROJECT_DIR
    / "outputs"
    / "anime-conflicts-excel"
    / "conflict-decisions.json"
)
BACKUP_DIR = PROJECT_DIR / "backups" / "anime-review"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "anime-conflicts-excel"
ANILIST_ENDPOINT = "https://graphql.anilist.co"


MANUAL_REVIEW = {
    "anime-excel-219-3904": {
        "anilistId": 162694,
        "title": "Kimi no Koto ga Daidaidaidaidaisuki na 100-nin no Kanojo",
        "year": 2023,
        "season": "Fall",
        "format": "Serie",
        "activeSeason": "S01",
        "chapters": 12,
    },
    "anime-excel-225-3912": {
        "anilistId": 153687,
        "title": "PSYCHO-PASS PROVIDENCE",
        "year": 2023,
        "season": "Spring",
        "format": "Película",
        "activeSeason": "S00",
        "chapters": 1,
    },
    "anime-excel-302-3955": {
        "anilistId": 169417,
        "title": "Re:Monster",
        "year": 2024,
        "season": "Spring",
        "format": "Serie",
        "activeSeason": "S01",
        "chapters": 12,
    },
    "anime-excel-349-4042": {
        "anilistId": 158928,
        "title": "SPY×FAMILY CODE: White",
        "year": 2023,
        "season": "Fall",
        "format": "Película",
        "activeSeason": "S00",
        "chapters": 1,
    },
    "anime-excel-357-4050": {
        "anilistId": 163134,
        "activeSeason": "S03",
        "chapters": 16,
        "format": "Serie",
        "year": 2024,
        "season": "Fall",
    },
    "anime-excel-361-4054": {
        "anilistId": 170732,
        "title": "Dungeon ni Deai wo Motomeru no wa Machigatteiru Darou ka V: Houjou no Megami-hen",
        "activeSeason": "S05",
        "chapters": 15,
        "format": "Serie",
        "year": 2024,
        "season": "Fall",
    },
    "anime-excel-471-4171": {
        "anilistId": 176246,
        "title": "mono",
        "alternativeTitles": ["Mono Weekend Animation"],
        "activeSeason": "S01",
        "chapters": 12,
        "format": "Serie",
        "year": 2025,
        "season": "Spring",
    },
    "anime-excel-528-4232": {
        "anilistId": 177271,
        "title": "Kakuriyo no Yadomeshi Ni",
        "alternativeTitles": ["Kakuriyo no Yadomeshi 2nd Season"],
        "activeSeason": "S02",
        "chapters": 12,
        "format": "Serie",
        "year": 2025,
        "season": "Fall",
    },
    "anime-excel-535-4239": {
        "anilistId": 181447,
        "title": "Saigo ni Hitotsu dake Onegai Shite mo Yoroshii Deshou ka",
        "activeSeason": "S01",
        "chapters": 13,
        "format": "Serie",
        "year": 2025,
        "season": "Fall",
    },
    "anime-excel-575-4279": {
        "anilistId": 187264,
        "title": "Yuusha Party wo Oidasareta Kiyou Binbou",
        "alternativeTitles": [
            "Yuusha Party wo Oidasareta Kiyoubinbou",
            "Jack-of-All-Trades, Party of None",
        ],
        "activeSeason": "S01",
        "chapters": 12,
        "format": "Serie",
        "year": 2026,
        "season": "Winter",
    },
    "anime-excel-600-4305": {
        "anilistId": 191718,
        "title": '"Omae Gotoki ga Maou ni Kateru to Omou na" to Yuusha Party wo Tsuihou Sareta node, Outo de Kimama ni Kurashitai',
        "alternativeTitles": ["Omagoto", "ROLL OVER AND DIE"],
        "activeSeason": "S01",
        "chapters": 12,
        "format": "Serie",
        "year": 2026,
        "season": "Winter",
    },
    "anime-excel-605-4310": {
        "anilistId": 185262,
        "title": "Hell Mode: Yarikomi-zuki no Gamer wa Haisettei no Isekai de Musou Suru",
        "alternativeTitles": [
            "HELL MODE: The Hardcore Gamer Dominates in Another World with Garbage Balancing"
        ],
        "activeSeason": "S01",
        "chapters": 12,
        "format": "Serie",
        "year": 2026,
        "season": "Winter",
    },
    "anime-excel-696-4401": {
        "anilistId": 209983,
        "title": "Hell Mode: Yarikomi-zuki no Gamer wa Haisettei no Isekai de Musou Suru 2nd Season",
        "activeSeason": "S02",
        "chapters": 13,
        "format": "Serie",
        "year": 2026,
        "season": "Summer",
    },
    "anime-excel-724-1005": {
        "anilistId": 177699,
        "title": "Koukaku Kidoutai (TV, 2026)",
        "alternativeTitles": [
            "Koukaku Kidoutai: THE GHOST IN THE SHELL",
            "THE GHOST IN THE SHELL",
        ],
        "activeSeason": "S01",
        "chapters": 10,
        "format": "Serie",
        "year": 2026,
        "season": "Summer",
    },
    "anime-excel-726-1007": {
        "anilistId": 209800,
        "title": "Yoroi Shinden Samurai Troopers Part 2",
        "alternativeTitles": ["Yoroi-Shinden Samurai Troopers Cour 2"],
        "activeSeason": "S02",
        "chapters": 12,
        "format": "Serie",
        "year": 2026,
        "season": "Summer",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes to anime.json.")
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp"
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def clean_description(value: object) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_manual_candidates() -> dict[int, dict[str, object]]:
    ids = sorted({int(item["anilistId"]) for item in MANUAL_REVIEW.values()})
    query = """
    query ($ids: [Int]) {
      Page(page: 1, perPage: 50) {
        media(id_in: $ids, type: ANIME) {
          id idMal format season seasonYear episodes status averageScore siteUrl genres
          description(asHtml: false)
          title { romaji english native }
          coverImage { extraLarge large medium }
          studios(isMain: true) { nodes { name } }
        }
      }
    }
    """
    body = json.dumps({"query": query, "variables": {"ids": ids}}).encode("utf-8")
    request = Request(
        ANILIST_ENDPOINT,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Altoidss-review/1.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    media = (((payload.get("data") or {}).get("Page") or {}).get("media") or [])
    return {int(item["id"]): item for item in media}


def unique_text(values: list[object]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


def map_format(api_format: object, chapters: int, current: str) -> tuple[str, str]:
    normalized = str(api_format or "").upper()
    if normalized == "MOVIE":
        return "Película", "S00"
    if normalized in {"OVA", "ONA", "SPECIAL"} and chapters == 1:
        return ("Película" if current == "Película" else "OVA"), "S00"
    return "Serie", ""


def rebuild_tags(record: dict[str, object]) -> None:
    record["tags"] = unique_text(
        [record.get("format"), record.get("viewingStatus"), record.get("productionStatus")]
    )


def candidate_from_anilist(item: dict[str, object]) -> dict[str, object]:
    titles = item.get("title") or {}
    cover = item.get("coverImage") or {}
    studios = (item.get("studios") or {}).get("nodes") or []
    genres = [str(value).strip() for value in item.get("genres") or [] if str(value).strip()]
    return {
        "title": titles.get("romaji") or titles.get("english") or "",
        "alternativeTitle": titles.get("english") or "",
        "alternativeTitles": [titles.get("native") or ""],
        "format": item.get("format") or "TV",
        "emissionYear": item.get("seasonYear") or 0,
        "emissionSeason": str(item.get("season") or "").title(),
        "chapters": item.get("episodes") or 0,
        "genre": genres[0] if genres else "Anime",
        "tags": genres[1:4],
        "image": cover.get("extraLarge") or cover.get("large") or cover.get("medium") or "",
        "description": clean_description(item.get("description")),
        "rating": round(float(item.get("averageScore") or 0) / 10, 1)
        if item.get("averageScore")
        else "",
        "sourceUrl": item.get("siteUrl") or "",
        "source": "anilist",
        "anilistId": str(item.get("id") or ""),
        "jikanId": str(item.get("idMal") or ""),
        "studio": studios[0].get("name") if studios else "",
    }


def apply_candidate(
    record: dict[str, object],
    candidate: dict[str, object],
    score: float,
    override: dict[str, object] | None = None,
) -> None:
    override = override or {}
    previous_title = str(record.get("title") or "")
    title = str(override.get("title") or candidate.get("title") or previous_title).strip()
    candidate_chapters = int(override.get("chapters") or candidate.get("chapters") or 0)
    chapters = candidate_chapters or int(record.get("chapters") or 0)
    target_format, default_season = map_format(
        override.get("format") or candidate.get("format"), chapters, str(record.get("format") or "")
    )
    if override.get("format"):
        target_format = str(override["format"])

    record["title"] = title
    record["alternativeTitles"] = unique_text(
        [
            previous_title,
            candidate.get("alternativeTitle"),
            *(candidate.get("alternativeTitles") or []),
            *(override.get("alternativeTitles") or []),
        ]
    )
    record["format"] = target_format
    record["chapters"] = chapters
    record["activeSeason"] = str(
        override.get("activeSeason") or default_season or record.get("activeSeason") or "S01"
    )
    if override.get("year") or candidate.get("emissionYear"):
        year = int(override.get("year") or candidate.get("emissionYear"))
        record["year"] = str(year)
        record["emissionYear"] = year
    if override.get("season") or candidate.get("emissionSeason"):
        record["emissionSeason"] = str(
            override.get("season") or candidate.get("emissionSeason")
        )

    for field in ("image", "description", "sourceUrl", "rating"):
        if candidate.get(field) not in {None, ""}:
            record[field] = candidate[field]
    if candidate.get("genre") and candidate.get("genre") != "Anime":
        record["genre"] = candidate["genre"]
    record["metadataGenres"] = unique_text(
        [candidate.get("genre"), *(candidate.get("tags") or [])]
    )
    if candidate.get("studio"):
        record["studio"] = candidate["studio"]
    for provider_id in ("jikanId", "anilistId", "kitsuId"):
        if candidate.get(provider_id):
            record[provider_id] = str(candidate[provider_id])
    record["externalTitle"] = candidate.get("title") or title
    record["metadataProvider"] = candidate.get("source") or "external"
    record["metadataMatchScore"] = round(float(score), 4)
    record["metadataUpdatedAt"] = datetime.now().astimezone().isoformat()
    record["reviewDecision"] = "OK" if not override else "CORRECCIÓN MANUAL"
    rebuild_tags(record)


def snapshot(record: dict[str, object]) -> dict[str, object]:
    fields = (
        "id", "title", "alternativeTitles", "format", "emissionYear",
        "emissionSeason", "activeSeason", "chapters", "image", "sourceUrl",
        "metadataProvider", "anilistId", "jikanId", "kitsuId",
    )
    return {field: record.get(field) for field in fields}


def main() -> None:
    args = parse_args()
    records = load_json(ANIME_PATH)
    report = load_json(REPORT_PATH)
    decisions = load_json(DECISIONS_PATH)
    records_by_id = {str(item.get("id") or ""): item for item in records}
    report_by_id = {str(item.get("id") or ""): item for item in report}

    counts = {
        "OK": sum(item.get("decision") == "OK" for item in decisions),
        "RECHAZAR": sum(item.get("decision") == "RECHAZAR" for item in decisions),
    }
    if counts != {"OK": 50, "RECHAZAR": 15}:
        raise SystemExit(f"Decisiones inesperadas: {counts}")
    rejected_ids = {item["id"] for item in decisions if item.get("decision") == "RECHAZAR"}
    if rejected_ids != set(MANUAL_REVIEW):
        raise SystemExit("Los 15 rechazos del Excel no coinciden con las correcciones manuales.")

    manual_candidates = fetch_manual_candidates()
    missing_anilist = sorted(
        int(item["anilistId"])
        for item in MANUAL_REVIEW.values()
        if int(item["anilistId"]) not in manual_candidates
    )
    if missing_anilist:
        raise SystemExit(f"AniList no devolvió estos ID confirmados: {missing_anilist}")

    changes = []
    for decision in decisions:
        record_id = decision["id"]
        record = records_by_id.get(record_id)
        report_item = report_by_id.get(record_id)
        if record is None or report_item is None:
            raise SystemExit(f"No se encontró el registro o reporte para {record_id}")
        before = snapshot(record)
        if decision["decision"] == "OK":
            apply_candidate(
                record,
                report_item["candidate"],
                float(report_item.get("score") or 1),
            )
        else:
            override = MANUAL_REVIEW[record_id]
            candidate = candidate_from_anilist(manual_candidates[int(override["anilistId"])])
            apply_candidate(record, candidate, 1.0, override)
        changes.append({"id": record_id, "before": before, "after": snapshot(record)})

    report_output = {
        "mode": "apply" if args.apply else "dry-run",
        "generatedAt": datetime.now().astimezone().isoformat(),
        "approvedFromExcel": 50,
        "manualCorrections": 15,
        "totalUpdated": len(changes),
        "changes": changes,
    }
    report_path = OUTPUT_DIR / "anime-review-apply-report.json"
    write_json_atomic(report_path, report_output)

    backup_path = None
    if args.apply:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / f"anime-before-reviewed-corrections-{timestamp}.json"
        shutil.copy2(ANIME_PATH, backup_path)
        write_json_atomic(ANIME_PATH, records)

    print(json.dumps({
        "mode": report_output["mode"],
        "approvedFromExcel": 50,
        "manualCorrections": 15,
        "totalUpdated": len(changes),
        "backup": str(backup_path) if backup_path else None,
        "report": str(report_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
