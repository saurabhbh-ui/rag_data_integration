from __future__ import annotations
from typing import Optional

from langchain_openai import AzureOpenAIEmbeddings

from ETL.document_processor.base.interfaces import Chunker
from ETL.document_processor.base.models import ProcessingConfig
from ETL.document_processor.chunkers.recursive_chunker import RecursiveChunker
from ETL.document_processor.chunkers.markdown_chunker import MarkdownChunker
from ETL.document_processor.chunkers.character_chunker import CharacterChunker

import logging

logger = logging.getLogger(__name__)


class ChunkerFactory:
    """Factory for creating chunker instances."""

    _chunkers = {
        "recursive": RecursiveChunker,
        "markdown": MarkdownChunker,
        "character": CharacterChunker,
    }

    @staticmethod
    def create_chunker(config: ProcessingConfig, embeddings: Optional[AzureOpenAIEmbeddings] = None) -> Chunker:
        strategy = config.chunking_strategy
        if hasattr(strategy, "value"):
            strategy = strategy.value

        if strategy not in ChunkerFactory._chunkers:
            logger.warning(
                f"Unknown chunking strategy '{strategy}'. Falling back to 'recursive'. "
                f"Supported: {list(ChunkerFactory._chunkers.keys())}"
            )
            strategy = "recursive"

        chunker_class = ChunkerFactory._chunkers[strategy]
        return chunker_class(config)

    @classmethod
    def register_chunker(cls, strategy: str, chunker_class: type[Chunker]) -> None:
        cls._chunkers[strategy] = chunker_class
        logger.info(f"Registered chunker for strategy '{strategy}'")

    @classmethod
    def get_supported_strategies(cls) -> list[str]:
        return list(cls._chunkers.keys())