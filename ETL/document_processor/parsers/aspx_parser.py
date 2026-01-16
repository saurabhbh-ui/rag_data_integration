
from __future__ import annotations
from pathlib import Path

from ETL.document_processor.parsers.base_parser import BaseParser
from ETL.document_processor.base.interfaces import Parser
from ETL.document_processor.base.models import ProcessingConfig
from ETL.tools.aspx_to_md import convert_aspx_to_markdown  # type: ignore

import logging

logger = logging.getLogger(__name__)


class AspxParser(BaseParser, Parser):
    """Parser for ASPX files using convert_aspx_to_markdown utility."""
    def __init__(self, config: ProcessingConfig | None = None):
        super().__init__(config)

    def supports_file_type(self, file_extension: str) -> bool:
        return file_extension.lower() == ".aspx"

    def parse(self, file_path: Path, file_metadata: dict, **kwargs) -> tuple[str, int]:
        content = convert_aspx_to_markdown(file_path)
        return content, 0