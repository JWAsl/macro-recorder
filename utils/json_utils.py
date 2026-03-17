"""
Utility functions for saving/opening recorded event data as a JSON file.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger("json_utils")


def save_file(filename: str, events: list[dict[str, Any]]) -> None:
    """
    Save a list of recorded events to a JSON file.

    Args:
        filename: Name of the file to save.
        events: List of events to serialize.

    Raises:
        OSError: If a general I/O error occurs.
        TypeError: If the file contains an object that can't be serialized.
    """
    try:
        recordings_dir = Path.cwd() / "recordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)
        filepath = recordings_dir / filename
        with filepath.open("w", encoding="utf-8") as fp:
            json.dump(events, fp, indent=4)
        logger.info("Saved as: %s", filepath)
    except (OSError, TypeError):
        logger.exception("Error saving file")


def open_file(filepath: str) -> Optional[list[dict[str, Any]]]:
    """
    Opens a JSON file and returns its contents.

    Args:
        filepath: The string representation of the path to the JSON file. 

    Returns:
        A list of events (dictionaries) if successful, or None if there's an error.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        json.JSONDecodeError: If the file content is not valid JSON.
        OSError: If a general I/O error occurs.
    """
    path = Path(filepath)
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError:
        logger.warning("File not found: %s", path)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in file %s", path)
    except OSError:
        logger.exception("Error opening file: %s", path)
    return None
