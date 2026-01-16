"""Weaviate setup."""

import logging

import weaviate
from weaviate.classes.config import Configure, DataType, Property, Tokenization

from ETL.tools.settings import weaviate_settings

logger = logging.getLogger(__name__)


def setup_weaviate() -> weaviate.Client:
    """Initialize Weaviate with collections optimized for hybrid search."""
    client = weaviate.connect_to_local(weaviate_settings.url)

    collection_name = weaviate_settings.collection_name
    if not client.collections.exists(collection_name):
        properties = [
            Property(
                name="content",
                data_type=DataType.TEXT,
                vectorize_property_name=True,
                index_filterable=True,
                index_searchable=True,
                tokenization=Tokenization.WORD,
            ),
            Property(
                name="file_id",
                data_type=DataType.TEXT,
                index_filterable=True,
                index_searchable=True,
            ),
            Property(
                name="metadata",
                data_type=DataType.OBJECT,
                nested_properties=[
                    Property(
                        name="source",
                        data_type=DataType.TEXT,
                        index_filterable=True,
                        index_searchable=True,
                    ),
                    Property(
                        name="keywords",
                        data_type=DataType.TEXT_ARRAY,
                        index_filterable=True,
                        index_searchable=True,
                    ),
                ],
            ),
        ]

        client.collections.create(
            name=collection_name,
            properties=properties,
            inverted_index_config=Configure.inverted_index(
                bm25_b=0.75,
                bm25_k1=1.2,
                index_timestamps=False,
                index_property_length=False,
                index_null_state=False,
                cleanup_interval_seconds=300,
            ),
        )
        msg = f"Created Weaviate collection: {collection_name}."
        logger.info(msg)
    else:
        logger.info("Weaviate collection already exists!")
    return client


def check_n_create_weaviate_collection() -> None:
    """Check and eventually create the collection."""
    try:
        client = setup_weaviate()

        # Verify hybrid search configuration (CORRECTED)
        for collection_name in client.collections.list_all():
            config = client.collections.get(
                collection_name,
            ).config.get()  # Get the config

    except Exception:
        if "client" in locals():
            client.close()
        raise
    if "client" in locals():
        client.close()


if __name__ == "__main__":
    check_n_create_weaviate_collection()
