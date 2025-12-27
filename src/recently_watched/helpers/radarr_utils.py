import requests
from recently_watched.helpers.config_loader import load_config
from recently_watched.helpers.logger import setup_logger

config = load_config()
logger = setup_logger("radarr")

RADARR_URL = config["radarr"]["url"].rstrip("/")
RADARR_API_KEY = config["radarr"]["api_key"]
ROOT_FOLDER = config["radarr"]["root_folder"]
TMDB_API_KEY = config["tmdb"]["api_key"]

HEADERS = {"X-Api-Key": RADARR_API_KEY}


def get_or_create_tag(tag_name: str) -> int:
    r = requests.get(f"{RADARR_URL}/api/v3/tag", headers=HEADERS)
    r.raise_for_status()
    for tag in r.json():
        if tag["label"].lower() == tag_name.lower():
            return tag["id"]

    logger.info(f"Creating Radarr tag: {tag_name}")
    r = requests.post(
        f"{RADARR_URL}/api/v3/tag",
        json={"label": tag_name},
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()["id"]


def _radarr_get_all_movies():
    r = requests.get(f"{RADARR_URL}/api/v3/movie", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def radarr_find_movie(title: str):
    """
    Returns the Radarr movie dict if title matches (case-insensitive), else None.
    Mirrors your existing title matching behavior.
    """
    title_l = title.lower()
    for movie in _radarr_get_all_movies():
        if movie.get("title", "").lower() == title_l:
            return movie
    return None


def radarr_movie_exists(title: str) -> bool:
    return radarr_find_movie(title) is not None


def radarr_set_monitored(movie, monitored: bool = True):
    """
    Update an existing Radarr movie to monitored=True.
    Radarr requires full movie object for PUT /movie.
    """
    if movie.get("monitored") is monitored:
        logger.info(f"Already monitored in Radarr: {movie.get('title')}")
        return

    movie_id = movie["id"]
    updated = dict(movie)
    updated["monitored"] = monitored

    logger.info(f"Setting monitored={monitored} in Radarr: {movie.get('title')}")
    r = requests.put(
        f"{RADARR_URL}/api/v3/movie/{movie_id}",
        json=updated,
        headers=HEADERS,
    )
    r.raise_for_status()


def search_tmdb(title: str):
    r = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        params={"api_key": TMDB_API_KEY, "query": title},
        timeout=30,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    return results[0] if results else None


def radarr_add_and_search(title: str, tag_names):
    tag_ids = [get_or_create_tag(t) for t in tag_names]

    looked_up = None
    try:
        looked_up = radarr_lookup_movie(title)
    except Exception as e:
        logger.warning(f"Radarr lookup failed for '{title}': {e}")

    if looked_up:
        resolved_title = looked_up.get("title", title)
        tmdb_id = looked_up.get("tmdbId")
        year = looked_up.get("year")
    else:
        tmdb = search_tmdb(title)
        if not tmdb:
            logger.warning(f"Could not resolve movie via Radarr lookup or TMDB: {title}")
            return
        resolved_title = tmdb["title"]
        tmdb_id = tmdb["id"]
        year = int(tmdb["release_date"][:4]) if tmdb.get("release_date") else None

    if not tmdb_id:
        logger.warning(f"No tmdbId resolved for: {title}")
        return

    # ✅ NEW: prevent duplicate adds
    existing_by_id = radarr_find_movie_by_tmdb_id(int(tmdb_id))
    if existing_by_id:
        logger.info(f"Already in Radarr by tmdbId: {existing_by_id.get('title')} -> forcing monitored")
        radarr_set_monitored(existing_by_id, True)
        return

    payload = {
        "title": resolved_title,
        "tmdbId": int(tmdb_id),
        "year": year,
        "qualityProfileId": 1,
        "rootFolderPath": ROOT_FOLDER,
        "monitored": True,
        "addOptions": {"searchForMovie": True},
        "tags": tag_ids,
    }

    logger.info(f"Adding movie to Radarr + searching: {resolved_title}")
    r = requests.post(f"{RADARR_URL}/api/v3/movie", json=payload, headers=HEADERS)
    r.raise_for_status()


def radarr_process_missing_titles(titles, tag_names):
    """
    For each title:
      - if exists in Radarr -> force monitored=True
      - else add + search
    """
    for title in titles:
        existing = radarr_find_movie(title)
        if existing:
            try:
                radarr_set_monitored(existing, True)
            except Exception as e:
                logger.error(f"Failed to set monitored for {title}: {e}")
        else:
            try:
                radarr_add_and_search(title, tag_names)
            except Exception as e:
                logger.error(f"Failed to add/search in Radarr for {title}: {e}")


def radarr_lookup_movie(title: str):
    """
    Uses Radarr's lookup endpoint to find a movie and return a suitable object
    (includes tmdbId and title). This avoids doing TMDB DNS from the script host.
    """
    r = requests.get(
        f"{RADARR_URL}/api/v3/movie/lookup",
        headers=HEADERS,
        params={"term": title},
        timeout=30,
    )
    r.raise_for_status()
    results = r.json()
    return results[0] if results else None

def radarr_find_movie_by_tmdb_id(tmdb_id: int):
    for movie in _radarr_get_all_movies():
        if movie.get("tmdbId") == tmdb_id:
            return movie
    return None

