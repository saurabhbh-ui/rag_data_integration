# document_processor/utils/exceptions.py

"""
Re-export custom exceptions from ETL.tools.exceptions
"""

from ETL.tools.exceptions import (  # type: ignore
    MaxRetriesError,
    SPOError,
    InterpretationError,
    DBError,
    ProcessingError,
    ChunkingError,
    VisionProcessingError,
    StorageError,
)

__all__ = [
    "MaxRetriesError",
    "SPOError",
    "InterpretationError",
    "DBError",
    "ProcessingError",
    "ChunkingError",
    "VisionProcessingError",
    "StorageError",
]