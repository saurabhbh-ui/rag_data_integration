# ETL.document_processor/parsers/excel_parser.py

from __future__ import annotations
from pathlib import Path
import pandas as pd

from ETL.document_processor.parsers.base_parser import BaseParser
from ETL.document_processor.base.interfaces import Parser
from ETL.document_processor.base.models import ProcessingConfig

import logging

logger = logging.getLogger(__name__)


class ExcelParser(BaseParser, Parser):
    """Parser for Excel (.xlsx) files: converts each sheet to markdown and concatenates."""
    def __init__(self, config: ProcessingConfig | None = None):
        super().__init__(config)

    def supports_file_type(self, file_extension: str) -> bool:
        return file_extension.lower() == ".xlsx"

    def parse(self, file_path: Path, file_metadata: dict, **kwargs) -> tuple[str, int]:
        try:
            all_sheets = pd.read_excel(file_path, sheet_name=None)
            parts: list[str] = []
            for sheet_name, df in all_sheets.items():
                try:
                    md_table = df.to_markdown(index=False)
                    section = f"\n\n# Sheet: {sheet_name}\n\n{md_table}\n"
                    parts.append(section)
                except Exception as e:
                    logger.warning(f"Failed to process sheet '{sheet_name}' in {file_path.name}: {e}")
                    continue
            return "\n\n".join(parts), 0
        except Exception as e:
            logger.error(f"Excel parsing failed for {file_path.name}: {e}")
            raise