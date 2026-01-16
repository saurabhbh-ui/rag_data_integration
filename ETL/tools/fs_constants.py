"""Some constant defined fot File System."""

from pathlib import Path

# Local folder to save files
#DOWNLOAD_DIR = Path("C:/Users/sa007769/Downloads/rag_etl/bis-gpt-rag-etl/intermediate_files")  # noqa: S108

project_root = Path(__file__).parent.parent.parent
DOWNLOAD_DIR = project_root / "intermediate_files"

# Create directory if it doesn't exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

#DOWNLOAD_DIR = Path("/tmp/")  # noqa: S108

# file with the fresh SPO metadata
NEW_METADATA_FILE = DOWNLOAD_DIR / "spo_new_files.json"

# previous SPO metadata file
OLD_METADATA_FILE = DOWNLOAD_DIR / "spo_old_files.json"

# new files to be processed
NEW_FILES = DOWNLOAD_DIR / "new_files.json"
UPDATED_FILES = DOWNLOAD_DIR / "changed_files.json"
DELETED_FILES = DOWNLOAD_DIR / "deleted_files.json"