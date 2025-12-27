import re
from openai import OpenAI
from recently_watched.helpers.config_loader import load_config

config = load_config()
client = OpenAI(api_key=config["openai"]["api_key"])


def normalize_title(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[\d]+\s*[\.\)\-]\s*", "", line)  # "1. Title" -> "Title"
    line = line.strip("-• ").strip()
    return line.strip()


def get_related_movies(movie_name: str, max_results: int = 15):
    prompt = (
        f"Suggest up to {max_results} movies related to '{movie_name}', "
        "including sequels, prequels, or movies in the same genre or style.\n"
        "Rules:\n"
        "- Only real movie titles (no made-up titles).\n"
        "- Do NOT output partial subtitles or fragments.\n"
        "- One title per line.\n"
        "- No descriptions.\n"
    )


    resp = client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {"role": "system", "content": "You only output movie titles."}, 
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        timeout=60,   # <— add this
    )

    raw = resp.choices[0].message.content or ""
    movies = []
    seen = set()
    for line in raw.splitlines():
        t = normalize_title(line)
        if not t:
            continue
        tl = t.lower()
        if tl in seen:
            continue
        # Filter obvious fragments that cause Radarr failures
        if len(t) < 3:
            continue
        seen.add(tl)
        movies.append(t)
    return movies[:max_results]

def get_contrast_movies(movie_name: str, max_results: int = 15):
    """
    Return movies that feel like a 'palate cleanser' / opposite vibe of movie_name.
    Output titles only.
    """
    prompt = f"""
You are a movie expert.

Task:
1) Infer the likely GENRES and VIBE of "{movie_name}" (tone, pacing, intensity, humor level, realism vs fantasy).
2) Define an 'opposite' viewing profile (a deliberate change of taste).
3) Recommend up to {max_results} REAL movies that strongly match that opposite profile.

Rules:
- Only real movie titles (no made-up titles).
- Avoid sequels/prequels/remakes of "{movie_name}".
- Avoid movies that are too similar in tone/genre.
- Prefer well-known, widely available films (mix of eras is ok).
- One title per line, no numbering, no extra text.
""".strip()

    resp = client.chat.completions.create(
        model="gpt-5.2",
        messages=[
            {"role": "system", "content": "You only output movie titles, one per line."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        timeout=60,   # <— add this
    )

    raw = resp.choices[0].message.content or ""
    movies = []
    seen = set()
    for line in raw.splitlines():
        t = normalize_title(line)
        if not t:
            continue
        tl = t.lower()
        if tl in seen:
            continue
        if len(t) < 3:
            continue
        seen.add(tl)
        movies.append(t)
    return movies[:max_results]

if __name__ == "__main__":
    import sys

    movie = sys.argv[1] if len(sys.argv) > 1 else "Inception"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    print(f"\nTesting ChatGPT utils for: {movie!r} (max_results={n})\n")

    # If you have multiple recommenders, call them here.
    # Adjust names to match your file.
    try:
        print("=== get_related_movies ===")
        recs = get_related_movies(movie, max_results=n)  # or however your signature is
        for r in recs:
            print("-", r)
    except Exception as e:
        print("ERROR in get_related_movies:", repr(e))

    # If you added the contrast recommender:
    if "get_contrast_movies" in globals():
        try:
            print("\n=== get_contrast_movies ===")
            recs = get_contrast_movies(movie, max_results=n)
            for r in recs:
                print("-", r)
        except Exception as e:
            print("ERROR in get_contrast_movies:", repr(e))
    else:
        print("\n(get_contrast_movies not found — add it or adjust function name)")

