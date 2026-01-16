"""Main file for the ETL."""  # noqa: INP001

import logging
import sys

from ETL.db_access.ops import record_operations_stats
from ETL.nodes.compare_kbs import compare_kbs
from ETL.nodes.delete_old_entries import delete_entries_with_id
from ETL.nodes.get_file_metadata_from_db import get_file_metadata_from_db
from ETL.nodes.get_file_metadata_from_spo import get_file_metadata_from_spo
from ETL.nodes.process_new_files import process_new_files
from ETL.tools.weaviate_setup import check_n_create_weaviate_collection
from ETL.document_processor.base.models import ProcessingConfig
from ETL.tools.settings import rag_app_settings
from ETL.tools.registry_utils import get_etl_sources

# Configure logging to write to stdout
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout
    ],
)
logger = logging.getLogger(__name__)


# Get app_id from settings
app_id = rag_app_settings.app_id
logger.info(f"Loading configuration for app_id: {app_id}")


# Fetch all ETL configurations from App Registry API
try:
    all_etl_configs = get_etl_sources()
    logger.info(f"Retrieved {len(all_etl_configs)} ETL configurations from App Registry")
except Exception as e:
    logger.error(f"Failed to retrieve ETL configurations from App Registry: {e}")
    logger.error("Cannot proceed without ETL configuration. Exiting...")
    sys.exit(1)


# Filter configuration for current app_id
filtered_configs = [item for item in all_etl_configs if item.applicationId == app_id]

# Create ProcessingConfig from registry values
if filtered_configs:
    registry_config = filtered_configs[0]
    logger.info(f"Found ETL configuration for app_id {app_id}")
    logger.info(f"  - applicationName: {registry_config.applicationName}")
    logger.info(f"  - parserType: {registry_config.parserType}")
    logger.info(f"  - chunkerType: {registry_config.chunkerType}")
    logger.info(f"  - chunkAugmentationMethod: {registry_config.chunkAugmentationMethod}")
    
    # Normalize chunk_augmentation_method: convert 'None' or None to 'none'
    chunk_method = registry_config.chunkAugmentationMethod
    if chunk_method in [None, 'None']:
        chunk_method = 'none'
        logger.info(f"  - Normalized chunkAugmentationMethod from '{registry_config.chunkAugmentationMethod}' to 'none'")
    
    config1 = ProcessingConfig(
        parser_type=registry_config.parserType or 'document_intelligence',
        chunking_strategy=registry_config.chunkerType or 'recursive',
        chunk_augment_method=chunk_method,
        document_page_stitching=True,
    )
    
    logger.info(f"ProcessingConfig created successfully:")
    logger.info(f"  - parser_type: {config1.parser_type}")
    logger.info(f"  - chunking_strategy: {config1.chunking_strategy}")
    logger.info(f"  - chunk_augment_method: {config1.chunk_augment_method}")
    logger.info(f"  - append_summary_to_chunks: {config1.append_summary_to_chunks}")
    logger.info(f"  - use_iterative_reconstruction: {config1.use_iterative_reconstruction}")
    logger.info(f"  - document_page_stitching: {config1.document_page_stitching}")
    
else:
    # No matching configuration found for app_id
    logger.warning(f"No ETL configuration found for app_id {app_id}")
    logger.warning(f"Available applicationIds: {[item.applicationId for item in all_etl_configs]}")
    
    # Option 1: Use default configuration (current behavior)
    logger.warning("Using default configuration")
    config1 = ProcessingConfig(
        chunking_strategy="recursive",
        parser_type='document_intelligence',
        chunk_augment_method='none',
        document_page_stitching=False,
    )
    logger.info("Using default ProcessingConfig")


USE_FILESYSTEM = False

check_n_create_weaviate_collection()

logger.info("getting metadata from DB...")
db_data = get_file_metadata_from_db(use_filesystem=USE_FILESYSTEM)

logger.info("getting metadata from SPO...")
spo_data = get_file_metadata_from_spo(use_filesystem=USE_FILESYSTEM)

logger.info("comparing metadata....")
if USE_FILESYSTEM is False:
    new_files, deleted_files, updated_files = compare_kbs(
        use_filesystem=USE_FILESYSTEM,
        new_data=spo_data,
        old_data=db_data,
    )
    msg = f"""There are: {len(new_files)} new files,
        and {len(updated_files)} updated files
        and {len(deleted_files)} deleted files."""
    logger.info(msg)
    if new_files:
        try:
            logger.info("New files to be added:")
            for f in new_files:
                msg = f"- {f['name']}"
                logger.info(msg)
            images_count_per_file_dict = process_new_files(new_files, config1)

            n_new_files = len(new_files)
        except Exception as e:
            # any error happened
            n_new_files = -1
            images_count_per_file_dict = {}
            logger.exception(str(e))  # noqa: TRY401
    else:
        n_new_files = 0
        images_count_per_file_dict = {}  # Changed default

    if deleted_files:
        try:
            logger.info("Old files to be deleted:")
            for f in deleted_files:
                msg = f["id"]
                logger.info(msg)
            delete_entries_with_id(deleted_files)

            n_deleted_files = len(deleted_files)
        except Exception as e:
            # any error happened
            n_deleted_files = -1
            logger.exception(str(e))  # noqa: TRY401

    else:
        n_deleted_files = 0

    if updated_files:
        try:
            logger.info("Files to be updated:")
            for f in updated_files:
                msg = f"- {f['name']}"
                logger.info(msg)
            # update = delete + add new
            delete_entries_with_id(updated_files)
            images_count_per_file_dict_updated = process_new_files(updated_files, config1)  ## added 
            images_count_per_file_dict.update(images_count_per_file_dict_updated) ## added

            n_updated_files = len(updated_files)
        except Exception as e:
            # any error happened
            n_updated_files = -1
            logger.exception(str(e))  # noqa: TRY401
    else:
        n_updated_files = 0

    # fill the report table in the DB
    if n_new_files == -1 and n_deleted_files == -1 and n_updated_files == -1:
        logger.error("Error happened during processing files, not recording stats")
    else:
        logger.info("Record operations in DB...")
        formatting = "{} - Images present and not supported".format(n_updated_files)
        record_operations_stats(
            n_new_files=n_new_files,
            n_updated_files=n_updated_files,
            n_deleted_files=n_deleted_files,
            images_count_per_file=images_count_per_file_dict
        )

else:
    compare_kbs(
        use_filesystem=USE_FILESYSTEM,
        new_data=spo_data,
        old_data=db_data,
    )

logger.info("All Right!")
