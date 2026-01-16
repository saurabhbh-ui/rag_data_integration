
from __future__ import annotations
from abc import ABC
from ETL.document_processor.base.models import ProcessingConfig


class BaseParser(ABC):
    """Base parser class with shared config."""
    def __init__(self, config: ProcessingConfig | None = None):
        self.config = config or ProcessingConfig()
