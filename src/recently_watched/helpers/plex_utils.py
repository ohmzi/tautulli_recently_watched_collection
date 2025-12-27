from plexapi.server import PlexServer
from recently_watched.helpers.config_loader import load_config
from recently_watched.helpers.logger import setup_logger

config = load_config()
logger = setup_logger("plex")

PLEX_URL = config["plex"]["url"]
PLEX_TOKEN = config["plex"]["token"]
MOVIE_LIBRARY = config["plex"]["movie_library_name"]

plex = PlexServer(PLEX_URL, PLEX_TOKEN)


def library():
    return plex.library.section(MOVIE_LIBRARY)


def find_plex_movie_by_title(title):
    logger.info(f"Searching Plex for: {title}")
    for movie in library().search(title):
        if movie.title.lower() == title.lower():
            return movie
    return None


def clear_collection(collection_name: str):
    """
    Remove the collection tag from every movie currently in that collection.
    """
    logger.info(f"Clearing collection: {collection_name}")

    # Plex returns all items tagged with the collection
    items = library().search(collection=collection_name)

    logger.info(f"Found {len(items)} items currently in collection '{collection_name}'")
    for item in items:
        remove_movie_from_collection(item, collection_name)


def add_movie_to_collection(movie, collection_name: str):
    """
    Add collection tag to a movie. Plex auto-creates the collection view.
    Handles plexapi method differences.
    """
    logger.info(f"Adding to collection '{collection_name}': {movie.title}")

    # Newer plexapi commonly has addCollection
    if hasattr(movie, "addCollection"):
        movie.addCollection(collection_name)
        return

    # Fallback: editTags is supported in many versions
    if hasattr(movie, "editTags"):
        movie.editTags("collection", [collection_name], locked=False)
        return

    # Last resort: try edit with collections kw if present
    try:
        movie.edit(collections=[collection_name])
    except Exception as e:
        raise RuntimeError(f"Could not add collection tag to {movie.title}: {e}")


def remove_movie_from_collection(movie, collection_name: str):
    """
    Remove a specific collection tag from a movie.
    """
    logger.info(f"Removing from collection '{collection_name}': {movie.title}")

    if hasattr(movie, "removeCollection"):
        movie.removeCollection(collection_name)
        return

    if hasattr(movie, "editTags"):
        # remove only this tag by re-setting without it
        current = [c.tag for c in getattr(movie, "collections", [])] or []
        new_list = [c for c in current if c.lower() != collection_name.lower()]
        movie.editTags("collection", new_list, locked=False)
        return

    # last resort: attempt edit
    current = [c.tag for c in getattr(movie, "collections", [])] or []
    new_list = [c for c in current if c.lower() != collection_name.lower()]
    try:
        movie.edit(collections=new_list)
    except Exception as e:
        raise RuntimeError(f"Could not remove collection tag from {movie.title}: {e}")

