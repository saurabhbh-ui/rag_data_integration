# ETL.document_processor/parsers/factory.py

"""
Factory for creating parser instances based on file type and parser type.
"""

from __future__ import annotations
from typing import Optional, Dict, Type

from azure.ai.documentintelligence import DocumentIntelligenceClient
from langchain_openai import AzureChatOpenAI

from ETL.document_processor.base.interfaces import Parser
from ETL.document_processor.base.models import ProcessingConfig
from ETL.document_processor.parsers.document_intelligence_parser import DocumentIntelligenceParser
from ETL.document_processor.parsers.vision_parser import VisionParser
from ETL.document_processor.parsers.text_parser import TextParser
from ETL.document_processor.parsers.docx_parser import DocxParser
from ETL.document_processor.parsers.aspx_parser import AspxParser
from ETL.document_processor.parsers.excel_parser import ExcelParser

import logging

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating parser instances."""
    _parsers: Dict[str, Dict[str, Type[Parser]]] = {
        "pdf": {
            "document_intelligence": DocumentIntelligenceParser,
            "vision": VisionParser,
        },
        "txt": {"text": TextParser},
        "text": {"text": TextParser},
        "md": {"text": TextParser},
        "docx": {"docx": DocxParser},
        "aspx": {"aspx": AspxParser},
        "xlsx": {"excel": ExcelParser},
    }

    @staticmethod
    def get_parser(
        file_type: str,
        parser_type: str,
        di_client: Optional[DocumentIntelligenceClient] = None,
        llm: Optional[AzureChatOpenAI] = None,
        config: Optional[ProcessingConfig] = None
    ) -> Parser:
        file_type = file_type.lower().lstrip(".")
        parser_type = parser_type.lower()

        if file_type not in ParserFactory._parsers:
            raise ValueError(f"Unsupported file type: {file_type}")

        if parser_type not in ParserFactory._parsers[file_type]:
            raise ValueError(
                f"Parser type '{parser_type}' not supported for file type '{file_type}'. "
                f"Available parsers: {list(ParserFactory._parsers[file_type].keys())}"
            )

        parser_class = ParserFactory._parsers[file_type][parser_type]

        if parser_class == DocumentIntelligenceParser:
            print("I am Creating DocumentIntelligenceParser")
            if not di_client:
                raise ValueError("Document Intelligence client required for DocumentIntelligenceParser")
            return DocumentIntelligenceParser(di_client, config)

        elif parser_class == VisionParser:
            print("I am Creating VisionParser")
            if not llm:
                raise ValueError("LLM client required for VisionParser")
            return VisionParser(llm, di_client, config)

        elif parser_class == TextParser:
            return TextParser(config)

        elif parser_class == DocxParser:
            print("I am Creating DocxParser")
            return DocxParser(config, llm)

        elif parser_class == AspxParser:
            return AspxParser(config)

        elif parser_class == ExcelParser:
            print("I am Creating ExcelParser")
            return ExcelParser(config)

        else:
            raise ValueError(f"Parser class {parser_class} not properly configured")

    @classmethod
    def register_parser(cls, file_type: str, parser_type: str, parser_class: Type[Parser]) -> None:
        file_type = file_type.lower().lstrip(".")
        parser_type = parser_type.lower()
        if file_type not in cls._parsers:
            cls._parsers[file_type] = {}
        cls._parsers[file_type][parser_type] = parser_class
        logger.info(f"Registered parser '{parser_type}' for file type '{file_type}'")

    @classmethod
    def get_supported_file_types(cls) -> list[str]:
        return list(cls._parsers.keys())

    @classmethod
    def get_supported_parsers_for_file_type(cls, file_type: str) -> list[str]:
        file_type = file_type.lower().lstrip(".")
        if file_type in cls._parsers:
            return list(cls._parsers[file_type].keys())
        return []