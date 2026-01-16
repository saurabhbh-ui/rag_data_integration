from __future__ import annotations
from pathlib import Path
from ETL.document_processor.parsers.base_parser import BaseParser
from ETL.document_processor.base.interfaces import Parser
from ETL.document_processor.base.models import ProcessingConfig

import logging

logger = logging.getLogger(__name__)


class TextParser(BaseParser, Parser):
    """Parser for .txt and .md files."""
    def __init__(self, config: ProcessingConfig | None = None):
        super().__init__(config)

    def supports_file_type(self, file_extension: str) -> bool:
        return file_extension.lower() in [".txt", ".text", ".md"]

    def parse(self, file_path: Path, file_metadata: dict, **kwargs) -> tuple[str, int]:
        try:
            content = file_path.read_text(encoding="utf-8")
            return content, 0
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            raise