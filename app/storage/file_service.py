import json
import os
from typing import Dict, Any

class FileService:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def read_json(self) -> Dict[str, Any]:
        """Reads a JSON file and returns its content. Returns an empty dict if the file is not found."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"WARNING: Could not load data from file. Starting with empty store. Error: {e}")
        return {"users": {}, "conversations": {}}

    def write_json(self, data: Dict[str, Any]) -> None:
        """Writes a dictionary to a JSON file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"ERROR: Failed to write data to file. Error: {e}")