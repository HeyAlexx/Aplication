from __future__ import annotations

import argparse
import html
import json
import random
import re
import shutil
import sys
import time
import unicodedata
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parents[1]
ANIME_PATH = PROJECT_DIR / "data" / "anime.json"
WORK_DIR = PROJECT_DIR / "backups" / "anime-enrichment"
STATE_PATH = WORK_DIR / "state.json"
DEFAULT_ENDPOINT = "http://localhost/altoidss/api/index.php?route=/discover/anime-kitsu/"
DEFAULT_DESCRIPTION = "Registro importado desde Anime Data V1.xlsx."
JIKAN_ENDPOINT = "https://api.jikan.moe/v4/anime"
ANILIST_ENDPOINT = "https://graphql.anilist.co"
KITSU_ENDPOINT = "https://kitsu.io/api/edge/anime"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Completa imágenes, enlaces y descripciones del anime importado desde Excel."
    )
    parser.add_argument("--batch-size", type=int, default=60)
    parser.add_argument("--requests-per-minute", type=int, default=60)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument(
        "--provider",
        choices=["auto", "jikan", "anilist", "kitsu", "local"],
        default="auto",
    )
    parser.add_argument("--retry-unmatched", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_json(path: Path, fallback: object) -> object:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def normalize_title(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.casefold().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def format_key(value: object) -> str:
    value = normalize_title(value)
    if value in {"pelicula", "movie"}:
        return "movie"
    if value in {"ova", "ona", "especial", "special"}:
        return value
    return "series"


def title_season(value: object) -> int | None:
    title = normalize_title(value)
    patterns = [
        r"\bseason\s+(\d+)\b",
        r"\b(\d+)(?:st|nd|rd|th)\s+season\b",
        r"\bpart\s+(\d+)\b",
        r"\b(\d+)s\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return int(match.group(1))
    return None


def expected_season(record: dict[str, object]) -> int:
    active_season = re.search(r"(\d+)", str(record.get("activeSeason") or ""))
    if active_season:
        return max(1, int(active_season.group(1)))
    return title_season(record.get("title")) or 1


def title_part(value: object) -> int | None:
    match = re.search(r"\bpart\s+(\d+)\b", normalize_title(value))
    return int(match.group(1)) if match else None


def trailing_title_number(value: object) -> int | None:
    match = re.search(r"\b(\d+)\s*$", normalize_title(value))
    return int(match.group(1)) if match else None


def candidate_score(record: dict[str, object], candidate: dict[str, object]) -> float:
    expected = normalize_title(record.get("title"))
    raw_candidate_titles = [
        candidate.get("title"),
        candidate.get("alternativeTitle"),
        *(candidate.get("alternativeTitles") or []),
    ]
    candidate_titles = {normalize_title(title) for title in raw_candidate_titles}
    candidate_titles.discard("")
    score = max((SequenceMatcher(None, expected, title).ratio() for title in candidate_titles), default=0.0)

    if expected in candidate_titles:
        score = 1.0

    expected_year = int(record.get("emissionYear") or 0)
    candidate_year = int(candidate.get("emissionYear") or 0)
    if expected_year and candidate_year:
        difference = abs(expected_year - candidate_year)
        score += 0.12 if difference == 0 else -0.08 if difference <= 1 else -0.22 if difference >= 4 else -0.12

    formats_match = format_key(record.get("format")) == format_key(candidate.get("format"))
    score += 0.06 if formats_match else -0.3
    wanted_season = expected_season(record)
    found_seasons = {season for title in raw_candidate_titles if (season := title_season(title)) is not None}

    if wanted_season in found_seasons:
        score += 0.2
    elif found_seasons:
        score -= 0.38
    elif wanted_season > 1:
        score -= 0.3

    expected_part = title_part(record.get("title"))
    found_parts = {part for title in raw_candidate_titles if (part := title_part(title)) is not None}
    if found_parts:
        if expected_part in found_parts:
            score += 0.08
        elif expected_part is None and found_parts != {1}:
            score -= 0.35
        elif expected_part not in found_parts:
            score -= 0.35

    expected_emission_season = str(record.get("emissionSeason") or "").casefold()
    candidate_emission_season = str(candidate.get("emissionSeason") or "").casefold()
    if expected_emission_season and candidate_emission_season:
        score += 0.05 if expected_emission_season == candidate_emission_season else -0.18

    expected_trailing_number = trailing_title_number(record.get("title"))
    candidate_trailing_numbers = {
        number for title in raw_candidate_titles
        if (number := trailing_title_number(title)) is not None
    }
    if candidate_trailing_numbers and expected_trailing_number not in candidate_trailing_numbers:
        score -= 0.35

    score = min(1.0, max(0.0, score))
    return min(score, 0.6) if not formats_match else score


def choose_match(record: dict[str, object], candidates: list[dict[str, object]]) -> tuple[dict[str, object] | None, float]:
    ranked = sorted(
        ((candidate_score(record, candidate), candidate) for candidate in candidates),
        key=lambda entry: entry[0],
        reverse=True,
    )
    if not ranked:
        return None, 0.0

    expected_title = normalize_title(record.get("title"))
    best_candidate_titles = {
        normalize_title(title)
        for title in [
            ranked[0][1].get("title"),
            ranked[0][1].get("alternativeTitle"),
            *(ranked[0][1].get("alternativeTitles") or []),
        ]
    }
    exact_title_match = expected_title in best_candidate_titles or max(
        (SequenceMatcher(None, expected_title, title).ratio() for title in best_candidate_titles if title),
        default=0.0,
    ) >= 0.97

    if ranked[0][0] < 0.8 and not (exact_title_match and ranked[0][0] >= 0.6):
        return None, ranked[0][0] if ranked else 0.0
    return ranked[0][1], ranked[0][0]


def request_candidates(endpoint: str, title: str, max_attempts: int = 4) -> list[dict[str, object]]:
    url = endpoint.rstrip("/") + "/" + quote(title, safe="")
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Altoidss-enrichment/1.0"})

    for attempt in range(1, max_attempts + 1):
        try:
            with urlopen(request, timeout=35) as response:
                payload = json.load(response)
            break
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == max_attempts:
                raise

            retry_after = error.headers.get("Retry-After") if error.headers else None
            try:
                delay = float(retry_after) if retry_after else 3 * (2 ** (attempt - 1))
            except ValueError:
                delay = 3 * (2 ** (attempt - 1))
            time.sleep(delay + random.uniform(0.2, 0.8))
        except (URLError, TimeoutError):
            if attempt == max_attempts:
                raise
            time.sleep((3 * (2 ** (attempt - 1))) + random.uniform(0.2, 0.8))

    data = payload.get("data", []) if isinstance(payload, dict) else []
    return [item for item in data if isinstance(item, dict)]


def request_external(request: Request, max_attempts: int = 1) -> dict[str, object]:
    for attempt in range(1, max_attempts + 1):
        try:
            with urlopen(request, timeout=35) as response:
                return json.load(response)
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == max_attempts:
                raise
            retry_after = error.headers.get("Retry-After") if error.headers else None
            try:
                delay = float(retry_after) if retry_after else 3 * (2 ** (attempt - 1))
            except ValueError:
                delay = 3 * (2 ** (attempt - 1))
            time.sleep(delay + random.uniform(0.2, 0.8))
        except (URLError, TimeoutError):
            if attempt == max_attempts:
                raise
            time.sleep((3 * (2 ** (attempt - 1))) + random.uniform(0.2, 0.8))

    return {}


def clean_description(value: object) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"<[^>]+>", "", text).strip()


def jikan_candidates(title: str) -> list[dict[str, object]]:
    url = JIKAN_ENDPOINT + "?" + urlencode({"q": title, "limit": 20, "sfw": "true"})
    payload = request_external(Request(url, headers={"Accept": "application/json", "User-Agent": "Altoidss-enrichment/2.0"}))
    candidates = []

    for item in payload.get("data", []):
        if not isinstance(item, dict):
            continue
        genres = [
            str(genre.get("name") or "").strip()
            for genre in [*(item.get("genres") or []), *(item.get("themes") or []), *(item.get("demographics") or [])]
            if isinstance(genre, dict) and str(genre.get("name") or "").strip()
        ]
        year = item.get("year") or ((item.get("aired") or {}).get("prop") or {}).get("from", {}).get("year")
        images = item.get("images") or {}
        candidates.append({
            "title": item.get("title") or "",
            "alternativeTitle": item.get("title_english") or "",
            "alternativeTitles": [item.get("title_japanese") or "", *(item.get("title_synonyms") or [])],
            "format": item.get("type") or "Serie",
            "emissionYear": year or 0,
            "emissionSeason": str(item.get("season") or "").title(),
            "genre": genres[0] if genres else "Anime",
            "tags": genres[1:4],
            "image": ((images.get("webp") or {}).get("large_image_url")
                      or (images.get("jpg") or {}).get("large_image_url")
                      or (images.get("jpg") or {}).get("image_url") or ""),
            "description": str(item.get("synopsis") or "").strip(),
            "rating": item.get("score") or "",
            "sourceUrl": item.get("url") or "",
            "source": "jikan",
            "jikanId": str(item.get("mal_id") or ""),
        })

    return candidates


def anilist_candidates(title: str) -> list[dict[str, object]]:
    query = """
    query ($search: String!) {
      Page(page: 1, perPage: 20) {
        media(search: $search, type: ANIME, isAdult: false) {
          id idMal format season seasonYear episodes averageScore siteUrl genres description(asHtml: false)
          title { romaji english native }
          coverImage { extraLarge large medium }
        }
      }
    }
    """
    body = json.dumps({"query": query, "variables": {"search": title}}).encode("utf-8")
    request = Request(
        ANILIST_ENDPOINT,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Altoidss-enrichment/2.0"},
        method="POST",
    )
    payload = request_external(request)
    candidates = []

    for item in (((payload.get("data") or {}).get("Page") or {}).get("media") or []):
        if not isinstance(item, dict):
            continue
        titles = item.get("title") or {}
        genres = [str(genre).strip() for genre in item.get("genres") or [] if str(genre).strip()]
        cover = item.get("coverImage") or {}
        candidates.append({
            "title": titles.get("romaji") or titles.get("english") or "",
            "alternativeTitle": titles.get("english") or "",
            "alternativeTitles": [titles.get("native") or ""],
            "format": item.get("format") or "Serie",
            "emissionYear": item.get("seasonYear") or 0,
            "emissionSeason": str(item.get("season") or "").title(),
            "genre": genres[0] if genres else "Anime",
            "tags": genres[1:4],
            "image": cover.get("extraLarge") or cover.get("large") or cover.get("medium") or "",
            "description": clean_description(item.get("description")),
            "rating": round(float(item.get("averageScore") or 0) / 10, 1) if item.get("averageScore") else "",
            "sourceUrl": item.get("siteUrl") or "",
            "source": "anilist",
            "anilistId": str(item.get("id") or ""),
            "jikanId": str(item.get("idMal") or ""),
        })

    return candidates


def kitsu_candidates(title: str) -> list[dict[str, object]]:
    url = KITSU_ENDPOINT + "?" + urlencode({"filter[text]": title, "page[limit]": 20})
    payload = request_external(Request(url, headers={"Accept": "application/vnd.api+json", "User-Agent": "Altoidss-enrichment/2.0"}))
    candidates = []

    for item in payload.get("data", []):
        if not isinstance(item, dict):
            continue
        attributes = item.get("attributes") or {}
        titles = attributes.get("titles") or {}
        start_date = str(attributes.get("startDate") or "")
        year_match = re.match(r"(\d{4})", start_date)
        poster = attributes.get("posterImage") or {}
        candidates.append({
            "title": attributes.get("canonicalTitle") or "",
            "alternativeTitle": titles.get("en_jp") or titles.get("en") or "",
            "alternativeTitles": list(titles.values()),
            "format": attributes.get("subtype") or "Serie",
            "emissionYear": int(year_match.group(1)) if year_match else 0,
            "emissionSeason": "",
            "genre": "Anime",
            "tags": [],
            "image": poster.get("original") or poster.get("large") or poster.get("medium") or "",
            "description": str(attributes.get("synopsis") or attributes.get("description") or "").strip(),
            "rating": round(float(attributes.get("averageRating") or 0) / 10, 1) if attributes.get("averageRating") else "",
            "sourceUrl": "https://kitsu.app/anime/" + quote(str(attributes.get("slug") or item.get("id") or "")),
            "source": "kitsu",
            "kitsuId": str(item.get("id") or ""),
        })

    return candidates


def lookup_record(provider: str, endpoint: str, record: dict[str, object]) -> tuple[dict[str, object] | None, float]:
    title = str(record.get("title") or "")
    lookups = {
        "local": lambda: request_candidates(endpoint, title),
        "jikan": lambda: jikan_candidates(title),
        "anilist": lambda: anilist_candidates(title),
        "kitsu": lambda: kitsu_candidates(title),
    }
    providers = [provider] if provider != "auto" else ["jikan", "anilist", "kitsu"]
    query_variants = [title]
    without_suffix = re.sub(r"\s+Anime\s*$", "", title, flags=re.IGNORECASE).strip()
    if without_suffix != title:
        query_variants.append(without_suffix)
    if title.casefold().startswith("mugen gacha"):
        query_variants.append("Mugen Gacha")
    if title.casefold().startswith("kanpekisugite"):
        query_variants.append("Kanpeki Sugite Kawai-ge ga Nai")
    if title.casefold().startswith("koko wa ore ni makasete"):
        query_variants.append("I Became a Legend After My 10 Year-Long Last Stand")
    if len(title) > 90:
        query_variants.append(re.split(r"[,\-]", title, maxsplit=1)[0].strip())
    query_variants = list(dict.fromkeys(filter(None, query_variants)))
    best_match = None
    best_score = 0.0
    last_error: Exception | None = None

    for selected_provider in providers:
        for query_title in query_variants:
            try:
                candidates = (
                    request_candidates(endpoint, query_title)
                    if selected_provider == "local"
                    else {
                        "jikan": jikan_candidates,
                        "anilist": anilist_candidates,
                        "kitsu": kitsu_candidates,
                    }[selected_provider](query_title)
                )
            except (HTTPError, URLError, TimeoutError, ValueError) as error:
                last_error = error
                if provider != "auto":
                    raise
                continue
            match, score = choose_match(record, candidates)
            if score > best_score:
                best_match, best_score = match, score
            if match is not None:
                return match, score

    if best_match is None and best_score == 0 and last_error is not None:
        raise last_error
    return (best_match, best_score) if best_score >= 0.8 else (None, best_score)


def lookup_record_legacy(endpoint: str, record: dict[str, object]) -> tuple[dict[str, object] | None, float]:
    candidates = request_candidates(endpoint, str(record.get("title") or ""))
    return choose_match(record, candidates)


def needs_enrichment(record: dict[str, object]) -> bool:
    return (
        record.get("source") == "excel-anime-data-v1"
        and (
            not str(record.get("image") or "").startswith("https://")
            or not str(record.get("sourceUrl") or "").startswith("https://")
            or record.get("description") in {None, "", DEFAULT_DESCRIPTION}
        )
    )


def enrich_record(record: dict[str, object], match: dict[str, object], score: float) -> None:
    image = str(match.get("image") or "")
    source_url = str(match.get("sourceUrl") or "")
    description = str(match.get("description") or "").strip()

    if image.startswith("https://"):
        record["image"] = image
    if source_url.startswith("https://"):
        record["sourceUrl"] = source_url
    if description and not description.startswith("Información obtenida"):
        record["description"] = description

    if match.get("genre") and match.get("genre") != "Anime":
        record["genre"] = match["genre"]

    record["metadataGenres"] = [match.get("genre"), *(match.get("tags") or [])]
    record["metadataGenres"] = list(dict.fromkeys(filter(None, record["metadataGenres"])))
    record["rating"] = match.get("rating") or record.get("rating", "")
    for provider_id in ("jikanId", "anilistId", "kitsuId"):
        if match.get(provider_id):
            record[provider_id] = match[provider_id]
    record["externalTitle"] = match.get("title")
    record["metadataProvider"] = match.get("source") or "external"
    record["metadataMatchScore"] = round(score, 4)
    record["metadataUpdatedAt"] = datetime.now().astimezone().isoformat()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1 or not 1 <= args.requests_per_minute <= 60 or not 1 <= args.workers <= 10:
        raise SystemExit("batch-size debe ser positivo, RPM debe estar entre 1 y 60 y workers entre 1 y 10.")

    records = load_json(ANIME_PATH, [])
    if not isinstance(records, list):
        raise SystemExit("anime.json no contiene una lista válida.")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    state = load_json(STATE_PATH, {"completed": [], "unmatched": {}, "errors": {}})
    completed = set(state.get("completed", []))
    unmatched = state.get("unmatched", {})
    errors = state.get("errors", {})
    records_by_id = {str(record.get("id") or ""): record for record in records}
    completed = {
        record_id for record_id in completed
        if record_id in records_by_id and not needs_enrichment(records_by_id[record_id])
    }
    completed.update(
        record_id for record_id, record in records_by_id.items()
        if record.get("metadataProvider") and not needs_enrichment(record)
    )
    errors = {
        record_id: details for record_id, details in errors.items()
        if record_id not in completed and record_id not in unmatched
    }

    pending = [
        record for record in records
        if needs_enrichment(record)
        and record.get("id") not in completed
        and (args.retry_unmatched or record.get("id") not in unmatched)
    ][: args.batch_size]

    if not pending:
        print(json.dumps({"message": "No hay registros pendientes para este lote."}, ensure_ascii=False))
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = WORK_DIR / f"anime-before-enrichment-{timestamp}.json"
    if not args.dry_run:
        shutil.copy2(ANIME_PATH, backup_path)

    interval = 60 / args.requests_per_minute
    matched_count = 0
    unmatched_count = 0
    error_count = 0

    def persist_state() -> None:
        if args.dry_run:
            return
        write_json_atomic(ANIME_PATH, records)
        write_json_atomic(STATE_PATH, {
            "completed": sorted(completed),
            "unmatched": unmatched,
            "errors": errors,
            "updatedAt": datetime.now().astimezone().isoformat(),
        })

    def process_result(position: int, record: dict[str, object], future: Future[tuple[dict[str, object] | None, float]]) -> None:
        nonlocal matched_count, unmatched_count, error_count
        record_id = str(record.get("id") or "")
        title = str(record.get("title") or "")

        try:
            match, score = future.result()

            if match is None:
                unmatched[record_id] = {
                    "title": title,
                    "bestScore": round(score, 4),
                    "attemptedAt": datetime.now().astimezone().isoformat(),
                }
                errors.pop(record_id, None)
                unmatched_count += 1
                status = f"sin coincidencia ({score:.2f})"
            else:
                enrich_record(record, match, score)
                completed.add(record_id)
                unmatched.pop(record_id, None)
                errors.pop(record_id, None)
                matched_count += 1
                status = f"{match.get('title')} ({score:.2f})"

            persist_state()
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            errors[record_id] = {
                "title": title,
                "error": str(error),
                "attemptedAt": datetime.now().astimezone().isoformat(),
            }
            error_count += 1
            status = f"error: {error}"
            persist_state()

        print(f"[{position}/{len(pending)}] {title}: {status}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        inflight: dict[Future[tuple[dict[str, object] | None, float]], tuple[int, dict[str, object]]] = {}
        next_position = 0
        last_submission = 0.0

        while next_position < len(pending) or inflight:
            if next_position < len(pending) and len(inflight) < args.workers:
                wait_time = interval - (time.monotonic() - last_submission)
                if last_submission and wait_time > 0:
                    time.sleep(wait_time)

                record = pending[next_position]
                future = executor.submit(lookup_record, args.provider, args.endpoint, record)
                inflight[future] = (next_position + 1, record)
                next_position += 1
                last_submission = time.monotonic()
                continue

            done, _ = wait(inflight, return_when=FIRST_COMPLETED)
            for future in done:
                position, record = inflight.pop(future)
                process_result(position, record, future)

    print(json.dumps({
        "requested": len(pending),
        "matched": matched_count,
        "unmatched": unmatched_count,
        "errors": error_count,
        "totalCompleted": len(completed),
        "backup": str(backup_path) if not args.dry_run else None,
        "state": str(STATE_PATH),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
