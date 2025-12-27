import yaml
from pathlib import Path

def load_config():
    """
    Loads config.yaml from the project config/ directory.
    """
    # Go up from helpers/ -> recently_watched/ -> src/ -> project root -> config/
    base_dir = Path(__file__).resolve().parents[3]
    config_path = base_dir / "config" / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at: {config_path}")
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

