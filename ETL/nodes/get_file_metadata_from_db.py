"""Retrieve unique couples of file_id and file_etag from a Weaviate database."""

from __future__ import annotations

import json
import logging

import weaviate
from ETL.tools.fs_constants import OLD_METADATA_FILE
from ETL.tools.settings import weaviate_settings


def save_to_json(files_data: list[dict[str, str]]) -> None:
    """Save the unique couples of file_id and file_etag to a JSON file."""
    with OLD_METADATA_FILE.open("w") as json_file:
        json.dump(files_data, json_file, indent=4)
    msg = "File metadata from DB saved to {OLD_METADATA_FILE}"
    logging.info(msg)  # noqa: LOG015


def load_unique_couples() -> list[dict[str, str]]:
    """Load unique couples of file_id and file_etag from the Weaviate DB."""
    client = weaviate.connect_to_local(weaviate_settings.url)

    try:
        collection = client.collections.get(weaviate_settings.collection_name)
        unique_couples = set()

        for item in collection.iterator():
            metadata = item.properties["metadata"]
            unique_couples.add((item.properties["file_id"], metadata["etag"]))

    finally:
        client.close()

    cp_as_list = list(unique_couples)

    return [{"id": entry[0], "etag": entry[1]} for entry in cp_as_list]


def get_file_metadata_from_db(*, use_filesystem: bool) -> None | dict:
    """Load unique couples from the DB and save them."""
    unique_couples = load_unique_couples()
    if use_filesystem:
        save_to_json(files_data=unique_couples)
        return None
    return unique_couples


if __name__ == "__main__":
    get_file_metadata_from_db(use_filesystem=True)
