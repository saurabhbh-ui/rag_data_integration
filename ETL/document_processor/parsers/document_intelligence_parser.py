
from __future__ import annotations
from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from ETL.document_processor.parsers.base_parser import BaseParser
from ETL.document_processor.base.interfaces import Parser
from ETL.document_processor.base.models import ProcessingConfig
from ETL.tools.parser import parse_pdf_docs  # type: ignore

import logging

logger = logging.getLogger(__name__)


class DocumentIntelligenceParser(BaseParser, Parser):
    """Parser for PDFs using Azure Document Intelligence."""
    def __init__(self, di_client: DocumentIntelligenceClient, config: ProcessingConfig | None = None):
        super().__init__(config)
        self.di_client = di_client

    def supports_file_type(self, file_extension: str) -> bool:
        return file_extension.lower() in [".pdf"]

    def parse(self, file_path: Path, file_metadata: dict, **kwargs) -> tuple[str, int]:
        msdb_entry, n_unprocessed_images = parse_pdf_docs(
            di_client=self.di_client,
            file_metadata={**file_metadata, "file_path": file_path}
        )
        content = msdb_entry.content or ""
        return content, n_unprocessed_images