import sys
import json
from pathlib import Path
from recently_watched.helpers.chatgpt_utils import get_contrast_movies
from recently_watched.helpers.radarr_utils import radarr_process_missing_titles
from recently_watched.helpers.plex_utils import find_plex_movie_by_title
from recently_watched.helpers.logger import setup_logger

logger = setup_logger("change_of_taste")

RADARR_TAGS = ["movies", "change-of-taste"]
COLLECTION_NAME = "Change of Taste"
JSON_FILE = "change_of_taste_collection.json"


def save_collection_to_json(movies, json_file):
    """
    Save collection movies to JSON file.
    Movies should be a list of dicts with 'title' and optionally 'rating_key'.
    """
    # Go up from helpers/ -> recently_watched/ -> src/ -> project root -> data/
    project_root = Path(__file__).resolve().parents[3]
    json_path = project_root / "data" / json_file
    
    try:
        with open(str(json_path), "w", encoding="utf-8") as f:
            json.dump(movies, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(movies)} movies to {json_file}")
    except Exception as e:
        logger.exception(f"Failed to save collection to {json_file}: {e}")
        raise


def run_change_of_taste_collection(movie_name: str, max_results: int = 15):
    """
    Process change of taste collection recommendations.
    Returns dict with stats: {"found_in_plex", "missing_in_plex", "saved_to_json", "sent_to_radarr"}
    """
    logger.info(f"Processing movie: {movie_name}")
    
    try:
        # Get recommendations from ChatGPT
        logger.info("Step 1: Getting contrast recommendations from ChatGPT...")
        recommendations = get_contrast_movies(movie_name, max_results=max_results)
        logger.info(f"  ✓ ChatGPT returned {len(recommendations)} contrast recommendations")

        collection_movies = []
        missing_in_plex = []
        missing_seen = set()

        # 1) Plex-first pass
        logger.info("Step 2: Checking movies in Plex...")
        for title in recommendations:
            try:
                plex_movie = find_plex_movie_by_title(title)
                if plex_movie:
                    # Store with rating key for faster lookup later
                    collection_movies.append({
                        "title": plex_movie.title,
                        "rating_key": str(plex_movie.ratingKey),
                        "year": getattr(plex_movie, "year", None),
                    })
                else:
                    logger.debug(f"  Missing in Plex: {title}")
                    key = title.strip().lower()
                    if key and key not in missing_seen:
                        missing_seen.add(key)
                        missing_in_plex.append(title.strip())
            except Exception as e:
                logger.warning(f"  Error checking '{title}' in Plex: {e}")
                # Continue processing other movies
                key = title.strip().lower()
                if key and key not in missing_seen:
                    missing_seen.add(key)
                    missing_in_plex.append(title.strip())

        # 2) Deduplicate missing list (preserve order)
        deduped = []
        seen = set()
        for t in missing_in_plex:
            tl = t.lower()
            if tl in seen:
                continue
            seen.add(tl)
            deduped.append(t)
        missing_in_plex = deduped

        logger.info(f"  ✓ Found {len(collection_movies)} movies in Plex")
        logger.info(f"  ✓ {len(missing_in_plex)} movies missing in Plex")

        # Save to JSON (will be applied to Plex by midnight script)
        saved_to_json = False
        if collection_movies:
            try:
                save_collection_to_json(collection_movies, JSON_FILE)
                logger.info(f"Step 3: Saved {len(collection_movies)} movies to {JSON_FILE}")
                logger.info(f"  ✓ Collection state saved (will be applied by midnight refresher)")
                saved_to_json = True
            except Exception as e:
                logger.error(f"  ✗ Failed to save collection to JSON: {e}")
                raise
        else:
            logger.warning(f"Step 3: No movies found in Plex to save to collection")

        # 3) Radarr processing for missing titles
        sent_to_radarr = 0
        if missing_in_plex:
            logger.info(f"Step 4: Processing {len(missing_in_plex)} missing movies in Radarr...")
            try:
                radarr_process_missing_titles(missing_in_plex, RADARR_TAGS)
                sent_to_radarr = len(missing_in_plex)
                logger.info(f"  ✓ Processed {len(missing_in_plex)} movies in Radarr")
            except Exception as e:
                logger.error(f"  ✗ Error processing movies in Radarr: {e}")
                # Don't raise - continue execution
                logger.warning(f"  Some movies may not have been added to Radarr")
        else:
            logger.info(f"Step 4: No missing movies to process in Radarr")
        
        return {
            "found_in_plex": len(collection_movies),
            "missing_in_plex": len(missing_in_plex),
            "saved_to_json": saved_to_json,
            "sent_to_radarr": sent_to_radarr,
        }
    except Exception as e:
        logger.exception(f"Error in run_change_of_taste_collection: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 tautulli_change_of_taste_collection.py "Movie Name"')
        sys.exit(1)

    movie_name = sys.argv[1]
    run_change_of_taste_collection(movie_name, max_results=15)

