"""Custom exceptions used in the app."""


class MaxRetriesError(Exception):
    """Exception raised when having too many failed calls to the service."""


class SPOError(Exception):
    """Exception raised for SharePoint Online related issues."""


class InterpretationError(Exception):
    """Exception raised for LLM interpretation of content."""


class DBError(Exception):
    """Exception raised when miss ineteract with the DB."""


#### Refinement 
class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass


class ChunkingError(ProcessingError):
    """Error during document chunking."""
    pass


class VisionProcessingError(ProcessingError):
    """Error during vision-based processing."""
    pass


class StorageError(ProcessingError):
    """Error storing data."""
    pass