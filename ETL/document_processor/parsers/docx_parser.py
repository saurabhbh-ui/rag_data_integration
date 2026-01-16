from __future__ import annotations
from pathlib import Path
from typing import Optional

from langchain_openai import AzureChatOpenAI

from ETL.document_processor.parsers.base_parser import BaseParser
from ETL.document_processor.base.interfaces import Parser
from ETL.document_processor.base.models import ProcessingConfig
from ETL.tools.process_docx import process_docx  # type: ignore

import logging

logger = logging.getLogger(__name__)


class DocxParser(BaseParser, Parser):
    """Parser for DOCX files using your existing process_docx utility."""
    def __init__(self, config: ProcessingConfig | None = None, llm: Optional[AzureChatOpenAI] = None):
        super().__init__(config)
        self.llm = llm

    def supports_file_type(self, file_extension: str) -> bool:
        return file_extension.lower() == ".docx"

    def parse(self, file_path: Path, file_metadata: dict, **kwargs) -> tuple[str, int]:
        entry = process_docx(
            docx_file=file_path,
            file_metadata=file_metadata,
            llm_multimodal=self.llm
        )
        return entry.content, 0