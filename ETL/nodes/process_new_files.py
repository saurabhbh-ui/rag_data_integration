"""Main file processor."""
import logging
import weaviate
from ETL.document_processor.main_processor.file_processor import FileProcessor
from ETL.document_processor.base.models import ProcessingConfig
from ETL.document_processor.utils.settings import weaviate_settings
from ETL.document_processor.utils.file_utils import download_file
from ETL.document_processor.utils.file_utils import convert_to_pdf

from tqdm import tqdm

logger = logging.getLogger(__name__)


def process_new_files(files: list[dict], config: ProcessingConfig) -> dict:
    """
    Process a list of files from SharePoint.
    
    Args:
        files: List of file metadata dicts
        config: Processing configuration
        
    Returns:
        Dict mapping filenames to unprocessed image counts
    """
    weaviate_client = weaviate.connect_to_local(weaviate_settings.url)
    try:
        n_chunks = None

        processor = FileProcessor(weaviate_client=weaviate_client, config=config)
        #processor = FileProcessor(config=config)
        unprocessed_per_file_dict = {}

        for file_metadata in tqdm(files):

            should_convert = (config.parser_type == 'vision')
            file_path = download_file(file_metadata, convert_to_pdf=should_convert)

            msg = f"processing file {file_metadata['name']}"
            logger.info(msg)

            file_metadata["file_path"] = file_path

            # Process file
            n_chunks, unprocessed = processor.process_file(
                file_path=file_path,
                file_metadata=file_metadata
            )

            # Store unprocessed items
            unprocessed_per_file_dict[file_metadata['name']] = unprocessed
            
            # Log results
            if unprocessed:
                unprocessed_str = ", ".join([f"{count} {item}" for item, count in unprocessed.items()])
                logger.info(
                    f"Completed {file_metadata['name']}: "
                    f"{n_chunks} chunks, Unprocessed: {unprocessed_str}"
                )
            else:
                logger.info(
                    f"Completed {file_metadata['name']}: "
                    f"{n_chunks} chunks, All items processed successfully"
                )

        return unprocessed_per_file_dict

    finally:
        weaviate_client.close()
