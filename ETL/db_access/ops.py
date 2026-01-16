"""Operations with DBs."""

import logging
import sys

import pandas as pd
import weaviate
from sqlalchemy.orm import Session
from ETL.tools.exceptions import DBError
from ETL.tools.settings import rag_app_settings, sql_server_settings, weaviate_settings
from weaviate.classes.query import MetadataQuery

from ETL.db_access.models import ETLReport

logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout
    ],
)
logger = logging.getLogger(__name__)


def read_weaviate_data() -> dict:
    """Retrieve and process document data from Weaviate vector database.

    Connects to the Weaviate instance, retrieves all documents in the collection,
    and processes the data to generate statistics about files and their chunks.

    Returns:
        dict: A dictionary containing:
            - 'total_files': The total number of unique files in the database
            - 'total_chunks': The total number of chunks across all files
            - 'files_in_db': Dictionary with file names as keys
                and their details (creation date, chunk count) as values

    """
    client = weaviate.connect_to_local(weaviate_settings.url)
    collection = client.collections.get(weaviate_settings.collection_name)

    data = []
    # Iterate through all objects, retrieving the creation_time metadata
    for article in collection.iterator(
        return_metadata=MetadataQuery(creation_time=True),
    ):
        # Build a list of dicts for DataFrame
        filename = article.properties["metadata"]["file_name"]
        content = article.properties["content"]
        link = article.properties["metadata"]["source"]
        creation_date = article.metadata.creation_time
        data.append(
            {
                "File Name": filename,
                "Creation Date": creation_date,
                "Content": content,
                "Link": link,
            },
        )

    client.close()
    df = pd.DataFrame(data)
    df["Creation Date"] = df["Creation Date"].dt.date

    # Group by filename and creation_date, count chunks, and collect content
    grouped_df = (
        df.groupby(["File Name", "Creation Date", "Link"])
        .agg(**{"Number of chunks": ("Content", "size"), "Content": ("Content", list)})
        .reset_index()
    )
    grouped_df["Creation Date"] = grouped_df["Creation Date"].astype(str)
    grouped_df = grouped_df.set_index("File Name")
    total_files = len(grouped_df)
    total_chunks = int(grouped_df["Number of chunks"].sum())
    files_in_db = grouped_df.to_dict("index")

    return {
        "total_files": total_files,
        "total_chunks": total_chunks,
        "files_in_db": files_in_db,
    }


def record_operations_stats(
    n_new_files: int,
    n_updated_files: int,
    n_deleted_files: int,
    images_count_per_file: dict
) -> None:
    """Record ETL operation statistics to the SQL database.

    Retrieves current vector database statistics using read_weaviate_data(),
    then creates and stores a new ETLReport record with the combined statistics.

    Args:
        n_new_files (int): Number of new files processed in the current ETL operation
        n_updated_files (int): Number of files updated in the current ETL operation
        n_deleted_files (int): Number of files deleted in the current ETL operation
        images_count_per_file (dict): Dictionary mapping filenames to unprocessed image counts
    Raises:
        DBError: If there's an error during database operations

    """
    logger.info("--- Reading Weaviate data...")
    vector_db_data = read_weaviate_data()

    # Add unprocessed images count to files_in_db
    for filename, file_data in vector_db_data["files_in_db"].items():
        if filename in images_count_per_file:
            file_data["Unprocessed_parts"] = images_count_per_file[filename]
        else:
            file_data["Unprocessed_parts"] = 0  # Default to 0 if not found


    engine = sql_server_settings.engine

    logger.info("--- Writing report to SQL Server...")
    with Session(engine) as session:
        try:
            rep2rec = ETLReport(
                app_id=rag_app_settings.app_id,
                new_files=n_new_files,
                updated_files=n_updated_files,
                deleted_files=n_deleted_files,
                total_files=vector_db_data["total_files"],
                total_chunks=vector_db_data["total_chunks"],
                files_in_db=vector_db_data["files_in_db"],
            )

            session.add(rep2rec)
            session.flush()  # getting the auto-generated id
            session.commit()

        except Exception as e:  # noqa: BLE001
            # Something gone wrong, rolling back all the changes within the sesion.
            session.rollback()
            raise DBError(str(e))  # noqa: B904
    logger.info("--- Report succesfully wrote.")
