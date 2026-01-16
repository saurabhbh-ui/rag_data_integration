
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from langchain.schema import Document
from langchain_openai import AzureOpenAIEmbeddings

from ETL.document_processor.base.interfaces import Chunker
from ETL.document_processor.base.models import ProcessingConfig, RAGEntry, RAGMetadata

import logging

logger = logging.getLogger(__name__)


class BaseChunker(Chunker, ABC):
    """Base class for chunkers."""
    def __init__(self, config: ProcessingConfig, embeddings: Optional[AzureOpenAIEmbeddings] = None):
        self.config = config
        self.embeddings = embeddings

    @abstractmethod
    def split_text(self, text: str, **kwargs) -> list[Document]:
        """
        Split text into chunks. Must be implemented by subclasses.
        
        Args:
            text: The text to split
            **kwargs: Additional parameters (e.g., metadata)
            
        Returns:
            List of Document objects with page_content and metadata
        """
        raise NotImplementedError
    

    def process_entry(self, data: RAGEntry, do_augment_metadata: bool = True) -> list[RAGEntry]:
        try:
            # Use split_text method to get chunks
            # Note: We don't pass metadata here because we preserve the original metadata 
            # from data.metadata using model_copy() below
            chunks = self.split_text(text=data.content)
            
            result = []
            for i, chunk_doc in enumerate(chunks):
                # Use model_copy() - this automatically copies ALL fields from the original metadata
                # No need to manually specify each field!
                meta = data.metadata.model_copy(deep=False)
                
                # Only reset fields that should be different for each chunk
                meta.chunk_idx = ""  # Will be set later in file_processor
                meta.keywords = []    # Will be generated per chunk
                meta.vector = []      # Will be generated per chunk
                
                # Create RAGEntry for this chunk
                result.append(RAGEntry(
                    content=chunk_doc.page_content,
                    metadata=meta,
                    file_id=data.file_id
                ))
                
            logger.debug(f"Processed entry {data.file_id}: created {len(result)} chunks from {len(data.content)} characters")
            return result

        except Exception as e:
            logger.error(f"Failed to process entry {data.file_id}: {e}", exc_info=True)
            raise
