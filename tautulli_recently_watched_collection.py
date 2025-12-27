#!/usr/bin/env python3
"""
Backward-compatible entry point for Tautulli automation.

This script is a wrapper that calls the main module from the new package structure.
It maintains compatibility with existing Tautulli configurations.
"""

import sys
from pathlib import Path

# Add src to path so we can import the package
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))

# Import and run the main function
try:
    from recently_watched.main import main
    exit_code = main()
    sys.exit(exit_code)
except ImportError as e:
    print(f"Error importing main module: {e}", file=sys.stderr)
    print(f"Project root: {project_root}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

