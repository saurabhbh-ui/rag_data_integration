
from __future__ import annotations
from typing import Optional, List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import AzureOpenAIEmbeddings

from ETL.document_processor.chunkers.base_chunker import BaseChunker
from ETL.document_processor.base.models import ProcessingConfig

import logging

logger = logging.getLogger(__name__)


class RecursiveChunker(BaseChunker):
    """Recursive character-based text splitter."""
    
    def __init__(self, config: ProcessingConfig, embeddings: Optional[AzureOpenAIEmbeddings] = None):
        super().__init__(config, embeddings)
        
        # Configure splitter with proper parameters
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=config.separators if config.separators else None,
        )
        
        logger.info(
            f"Initialized RecursiveChunker with chunk_size={config.chunk_size}, "
            f"chunk_overlap={config.chunk_overlap}"
        )

    def split_text(self, text: str, **kwargs) -> List[Document]:
        """
        Split text into chunks using recursive character splitting.
        
        Args:
            text: The text to split
            **kwargs: Optional metadata to attach to chunks
            
        Returns:
            List of Document objects with page_content and metadata
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Log text length for debugging
        logger.debug(f"Splitting text of length {len(text)} characters")
        
        metadata = kwargs.get("metadata", {})
        
        chunks = self._splitter.split_text(text)
        
        documents = [
            Document(page_content=chunk, metadata=metadata.copy())
            for chunk in chunks
        ]
        
        logger.debug(f"Created {len(documents)} chunks from input text")
        
        return documents
