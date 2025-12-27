# Recently Watched Collection - Tautulli Automation

**Version:** 1.0.0

**Table of Contents**  
- [Overview](#overview)  
- [Architecture & Flow](#architecture--flow)
- [Features](#features)  
- [Requirements](#requirements)  
- [Installation & Setup](#installation--setup)  
  - [1. Prerequisites](#1-prerequisites)  
  - [2. Prepare Your `config.yaml`](#2-prepare-your-configyaml)  
  - [3. Configure Collection Refresher (Optional)](#3-configure-collection-refresher-optional)
  - [4. Set Up Tautulli Automation](#4-set-up-tautulli-automation)
- [Project Structure](#project-structure)
- [Usage](#usage)

---

## Overview

This script automates the process of:

1. **Generating movie recommendations via OpenAI** based on recently watched movies
2. **Checking Plex for existing recommendations**
3. **Adding missing movies to Radarr**
4. **Maintaining two dynamic Plex collections:**
   - "Based on your recently watched movie" - Similar recommendations
   - "Change of Taste" - Contrasting recommendations
5. **Optional collection refresher** to randomize and update collection order during off-peak hours

---

## Architecture & Flow

### Entry Point
The main script `src/recently_watched/main.py` (or `tautulli_recently_watched_collection.py` for backward compatibility) is triggered by Tautulli when a movie is watched. It accepts two arguments:
- Movie title (from Tautulli)
- Media type (should be "movie")

### Execution Pipeline

The script follows this flow:

1. **Initialization** (`recently_watched/helpers/`)
   - Loads configuration from `config/config.yaml`
   - Connects to Plex server
   - Initializes logging

2. **Recommendation Generation** (`recently_watched/helpers/chatgpt_utils.py`)
   - Uses OpenAI GPT to generate up to 15 movie suggestions based on the recently watched movie
   - Generates two types of recommendations:
     - **Similar movies** (for "Based on your recently watched movie" collection)
     - **Contrasting movies** (for "Change of Taste" collection)

3. **Plex Lookup** (`recently_watched/helpers/plex_utils.py`)
   - Searches Plex library for each recommended movie
   - Uses rating keys for faster lookups when available
   - Separates movies into: found in Plex vs. missing

4. **Radarr Integration** (`recently_watched/helpers/radarr_utils.py`)
   - For movies not found in Plex:
     - Looks up movie in Radarr by title
     - If exists but unmonitored, sets to monitored
     - If missing, adds to Radarr with:
       - Configurable root folder
       - Quality profile
       - Custom tags
       - Triggers automatic search

5. **Collection State Management**
   - Saves collection movies to JSON files:
     - `data/recently_watched_collection.json` - Similar recommendations
     - `data/change_of_taste_collection.json` - Contrasting recommendations
   - Stores movies with title, rating_key, and year for faster Plex lookups

6. **Collection Refresher** (`recently_watched/refresher.py`) - *Optional*
   - Can run as part of main script (if enabled in config) or independently
   - Reads both collection JSON files
   - Randomizes the order of movies in memory
   - Removes all items from each Plex collection
   - Adds all items back in randomized order
   - Designed to run during off-peak hours to avoid overwhelming the server

### Supporting Modules

- **`config_loader.py`**: Loads and validates YAML configuration
- **`logger.py`**: Sets up structured logging with step context tracking
- **`plex_utils.py`**: Plex integration utilities (search, library access)
- **`radarr_utils.py`**: Radarr API integration
- **`chatgpt_utils.py`**: OpenAI API integration for recommendations

---

## Features

- **GPT Recommendations:**  
  Generates up to 15 movie suggestions based on a recently watched movie, including:
  - Similar movies (tone, themes, atmosphere)
  - Contrasting movies (different genres, styles, moods)

- **Dual Collection System:**  
  - **"Based on your recently watched movie"**: Movies similar to what you just watched
  - **"Change of Taste"**: Movies that offer a different experience

- **Plex Integration:**  
  - Searches Plex library for each recommended title
  - Uses rating keys for faster lookups
  - Maintains two dedicated collections with dynamic updates

- **Radarr Automation:**  
  - If a recommended title is not in Plex, the script adds it to Radarr
  - Configurable root folder, quality profile, and tags
  - Automatically triggers search for newly added movies
  - If movie already exists in Radarr but is unmonitored, sets it to monitored

- **Collection Refresher:**  
  - Optional script to randomize and refresh collection order during off-peak hours
  - Can run automatically as part of main script or independently via bash script
  - Configurable via `run_collection_refresher` boolean in `config/config.yaml`
  - Handles large collections gracefully with progress logging
  - Filters non-movie items automatically
  - Detailed error handling and connection timeout management

- **YAML Configuration:**  
  - No hardcoded credentials
  - All API keys, file paths, and server URLs are loaded from `config/config.yaml`
  - Configurable script execution options
  - Data files automatically resolved to `data/` directory

- **Structured Logging:**  
  - Step-based logging with timing information
  - Context-aware log messages
  - Pipeline summary statistics
  - Enhanced logging for collection refresher decisions and execution

---

## Requirements

1. **Core Services:**
   - Plex Media Server
   - Tautulli
   - Radarr (for automatic movie downloads)

2. **APIs:**
   - OpenAI API Key (required for recommendations)

3. **Python Dependencies:**
   - `requests` (for API calls)
   - `PyYAML` (for configuration)
   - `plexapi` (for Plex integration)
   - `openai` (for GPT recommendations)

---

## Installation & Setup

### 1. Prerequisites

- **Plex, Tautulli, and Radarr** must already be installed and working.
- You'll need valid credentials for each service (tokens, API keys, etc.).

### 2. Prepare Your `config.yaml`

1. Create or edit `config/config.yaml` in the project with your real credentials:

```yaml
plex:
  url: "http://localhost:32400"
  token: "YOUR_PLEX_TOKEN"
  movie_library_name: "Movies"

openai:
  api_key: "sk-proj-XXXXXXXXXXXXXXXXXXX"
  recommendation_count: 15

radarr:
  url: "http://localhost:7878"
  api_key: "YOUR_RADARR_API_KEY"
  root_folder: "/path/to/Movies"
  tag_name: "movies"

scripts_run:
  run_plex_duplicate_cleaner: false  # Change to true if you want to Run Plex Duplicate Cleaner
  run_radarr_monitor_confirm_plex: false  # Change to true if you want to Run Radarr Plex Monitor
  run_collection_refresher: false  # Change to true if you want to run Collection Refresher as part of main script. If false, run it independently via src/scripts/run_refresher.sh
```

2. Make sure `config/config.yaml` is placed in the project and will be accessible to your scripts.

### 3. Configure Collection Refresher (Optional)

The collection refresher script (`recently_watched/refresher.py`) can run in two modes:

**Option A: Run as part of main script (Integrated)**
- Set `run_collection_refresher: true` in `config/config.yaml` under `scripts_run`
- The refresher will automatically run at the end of each main script execution
- Useful if you want the collections updated immediately after recommendations are added
- Note: This may extend script execution time for large collections

**Option B: Run independently (Recommended for large collections)**
- Set `run_collection_refresher: false` in `config/config.yaml` (default)
- Run the refresher separately using the bash script:
  ```bash
  ./src/scripts/run_refresher.sh
  ```
- Or schedule it to run during off-peak hours via cron:
  ```bash
  # Run at midnight every day
  0 0 * * * /path/to/project/src/scripts/run_refresher.sh --no-pause
  ```
- This is recommended for large collections as the reordering process can take time

**Bash Script Options:**
- `--dry-run`: Show what would be done without actually updating Plex
- `--verbose`: Enable debug-level logging
- `--no-pause`: Don't pause at the end (for automated runs)
- `--log-file`: Also save output to a log file with timestamp
- `--help`: Show help message

### 4. Set Up Tautulli Automation

To have Tautulli automatically call your script whenever someone finishes watching a movie:

1. Open Tautulli → Settings → Notification Agents.
2. Click Add a new notification agent and choose **Script**.
3. **Script Folder**: Browse to the folder where the script is located (e.g., `/path/to/project` or the mounted volume path).
4. **Script File**: Select `tautulli_recently_watched_collection.py` (backward-compatible wrapper in project root).
5. **Description**: Provide a friendly name (e.g., "Recently Watched Collection Script").
6. **Trigger**: Choose **Watched** (so the script runs when a user finishes watching a movie).
7. **Arguments**: Under Watched arguments, pass:
   ```bash
   "{title}" "{media_type}"
   ```
   This passes both the movie title and media type to the script.
8. **Test Notification**:  
   Click Test → select your script → provide `"Inception (2010)"` as the first argument and `movie` as the second argument.
9. **Verify**:  
   Check Tautulli's logs to see if the script ran successfully and view the output.

---

## Project Structure

```
tautulli_recently_watched_collection/
├── config/
│   └── config.yaml                         # Configuration file
├── data/                                    # Generated data files
│   ├── recently_watched_collection.json    # Similar recommendations (generated)
│   ├── change_of_taste_collection.json     # Contrasting recommendations (generated)
│   └── logs/                                # Log files (optional)
├── src/
│   ├── recently_watched/                   # Main Python package
│   │   ├── __init__.py
│   │   ├── main.py                          # Main entry point
│   │   ├── refresher.py                     # Collection refresher script
│   │   └── helpers/                         # Helper modules
│   │       ├── chatgpt_utils.py             # OpenAI integration
│   │       ├── config_loader.py              # YAML config loader
│   │       ├── logger.py                     # Logging setup
│   │       ├── plex_utils.py                 # Plex integration
│   │       ├── radarr_utils.py               # Radarr integration
│   │       └── tautulli_change_of_taste_collection.py  # Change of taste logic
│   └── scripts/                             # Executable scripts
│       └── run_refresher.sh                 # Bash script to run refresher independently
├── docs/
│   └── README.md                           # This file
└── tautulli_recently_watched_collection.py  # Backward-compatible entry point
```

---

## Usage

### Running the Main Script

The script is typically triggered automatically by Tautulli when a movie finishes. You can also run it manually:

```bash
python3 tautulli_recently_watched_collection.py "Movie Title" movie
```

Or using the new package structure:

```bash
cd /path/to/project
export PYTHONPATH="$PWD/src:$PYTHONPATH"
python3 src/recently_watched/main.py "Movie Title" movie
```

### Running the Collection Refresher

**As part of main script:**
- Set `run_collection_refresher: true` in `config/config.yaml`
- The refresher will run automatically after recommendations are processed

**Independently:**
```bash
./src/scripts/run_refresher.sh [--dry-run] [--verbose] [--no-pause] [--log-file]
```

**Scheduled (cron):**
```bash
# Run at midnight every day
0 0 * * * /path/to/project/src/scripts/run_refresher.sh --no-pause
```

---

**Now whenever Tautulli detects that a user has finished watching a movie, it will trigger your script with the movie's title. With each run, your collections become more finely curated.**

**Version 2.1.0 Changes:**
- **Professional project structure**: Reorganized into `src/`, `config/`, `data/`, and `docs/` directories
- Added `refresher.py` script for randomizing and refreshing collection order
- Added `run_collection_refresher` configuration option to control refresher execution
- Enhanced logging throughout scripts with clear start/end markers and decision explanations
- Collection refresher can run as part of main script or independently via bash script
- Improved error handling and connection timeout management
- Added bash script wrapper (`src/scripts/run_refresher.sh`) with options for dry-run, verbose logging, and log file output
- All imports updated to use `recently_watched` package structure

**Tip: Add the collections to your Home screen and position them at the very top—right beneath the Continue Watching list.**

**Enjoy using this script! I hope it enhances your movie selection. If you encounter any issues or have ideas for enhancements, feel free to open an issue or submit a pull request.**

---

## License

This project is provided "as is" without warranty of any kind. You are free to use, modify, and distribute this code as per the [MIT License](https://opensource.org/licenses/MIT).

