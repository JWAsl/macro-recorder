import json
from pathlib import Path


def save_file(filename, saved_inputs) -> None:
    try:
        recordings_dir = Path.cwd() / "recordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)
        filepath = recordings_dir / filename
        with open(filepath, 'w') as outfile:
            json.dump(saved_inputs, outfile, indent=4)
        print(f"Saved as: {filepath}")
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error saving file: {e}")


def open_file(filepath):
    filepath = Path(filepath)
    try:
        with open(filepath, 'r') as jsonfile:
            return json.load(jsonfile)
    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in file {filepath}: {e}")
    return None
