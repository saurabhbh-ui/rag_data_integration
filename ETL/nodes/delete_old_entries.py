"""Delete stuff from weaviate DB."""

from __future__ import annotations

import weaviate
from ETL.tools.settings import weaviate_settings
from weaviate.classes.query import Filter


def delete_entries_with_id(deleted_files: list[dict]) -> None:
    """Delete entries in  the DB that correspond to the given IDs."""
    file_ids = [f["id"] for f in deleted_files]
    client = weaviate.connect_to_local(weaviate_settings.url)

    try:
        collection = client.collections.get(weaviate_settings.collection_name)

        collection.data.delete_many(
            where=Filter.by_property("file_id").contains_any(file_ids),
        )

    finally:
        client.close()
