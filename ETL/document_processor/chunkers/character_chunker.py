
from __future__ import annotations
from typing import List, Optional

from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_openai import AzureOpenAIEmbeddings

from ETL.document_processor.chunkers.base_chunker import BaseChunker
from ETL.document_processor.base.models import ProcessingConfig

import logging

logger = logging.getLogger(__name__)


class CharacterChunker(BaseChunker):
    """Simple character-based text splitter with fixed separator."""
    
    def __init__(self, config: ProcessingConfig, embeddings: Optional[AzureOpenAIEmbeddings] = None):
        super().__init__(config, embeddings)
        
        self._splitter = CharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separator="\n\n",  # Split on double newlines
            length_function=len,
            is_separator_regex=False,
        )
        
        logger.info(
            f"Initialized CharacterChunker with chunk_size={config.chunk_size}, "
            f"chunk_overlap={config.chunk_overlap}, separator='\\n\\n'"
        )

    def split_text(self, text: str, **kwargs) -> List[Document]:
        """
        Split text into chunks using character-based splitting.
        
        Args:
            text: The text to split
            **kwargs: Optional metadata to attach to chunks
            
        Returns:
            List of Document objects with page_content and metadata
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        logger.debug(f"Splitting text of length {len(text)} characters")
        
        # Extract metadata from kwargs if provided
        metadata = kwargs.get("metadata", {})
        
        # Use split_text method
        chunks = self._splitter.split_text(text)
        
        # Convert to Document objects
        documents = [
            Document(page_content=chunk, metadata=metadata.copy())
            for chunk in chunks
        ]
        
        logger.debug(f"Created {len(documents)} chunks from input text")
        
        return documents
