"""Compare metadata."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ETL.tools.fs_constants import (
    DELETED_FILES,
    NEW_FILES,
    NEW_METADATA_FILE,
    OLD_METADATA_FILE,
    UPDATED_FILES,
)


# Load the JSON files
def load_json(file_path: Path) -> dict:
    """Read dict from json."""
    with file_path.open() as file:
        return json.load(file)


# Compare JSON data based on file_etag
def compare_dicts(old_data: dict, new_data: dict) -> tuple:
    """Compare dicts."""
    old_files = {file["id"]: file for file in old_data}
    new_files = {file["id"]: file for file in new_data}

    new_files_list = []
    deleted_files_list = []
    updated_files_list = []

    # Find new and updated files
    for file_id, new_file in new_files.items():
        if file_id not in old_files:
            new_files_list.append(new_file)
        elif new_file["etag"] != old_files[file_id]["etag"]:
            updated_files_list.append(new_file)

    # Find deleted files
    for file_id, old_file in old_files.items():
        if file_id not in new_files:
            deleted_files_list.append(old_file)

    return new_files_list, deleted_files_list, updated_files_list


# Write results to JSON files
def write_json(file_path: Path, data: dict) -> None:
    """Write the data in a json."""
    with file_path.open("w") as file:
        json.dump(data, file, indent=4)


# Main function
def compare_kbs(
    *,
    use_filesystem: bool,
    new_data: dict | None = None,
    old_data: dict | None = None,
) -> None | tuple:
    """Compare thge metadata to discover new, updated and deleted files."""
    if old_data is None:
        old_data = load_json(OLD_METADATA_FILE)
    if new_data is None:
        new_data = load_json(NEW_METADATA_FILE)

    new_files, deleted_files, updated_files = compare_dicts(old_data, new_data)

    if use_filesystem:
        write_json(NEW_FILES, new_files)
        write_json(DELETED_FILES, deleted_files)
        write_json(UPDATED_FILES, updated_files)
        return None
    return new_files, deleted_files, updated_files


# Example usage
if __name__ == "__main__":
    compare_kbs(use_filesystem=True)
