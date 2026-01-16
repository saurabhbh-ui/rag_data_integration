
from __future__ import annotations
from typing import List, Optional

from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.schema import Document
from langchain_openai import AzureOpenAIEmbeddings

from ETL.document_processor.chunkers.base_chunker import BaseChunker
from ETL.document_processor.base.models import ProcessingConfig

import logging

logger = logging.getLogger(__name__)


class MarkdownChunker(BaseChunker):
    """Chunker that splits text by markdown headers."""
    
    def __init__(self, config: ProcessingConfig, embeddings: Optional[AzureOpenAIEmbeddings] = None):
        super().__init__(config, embeddings)
        
        headers = config.markdown_headers or [("#", "h1"), ("##", "h2"), ("###", "h3")]
        self._splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers, return_each_line=True, strip_headers=False)
        
        logger.info(f"Initialized MarkdownChunker with headers: {headers}")

    def split_text(self, text: str, **kwargs) -> List[Document]:
        """
        Split text into chunks using markdown header-based splitting.
        
        Args:
            text: The text to split
            **kwargs: Optional metadata to attach to chunks
            
        Returns:
            List of Document objects with page_content and metadata
        """
        if not text or not text.strip():
            logger.warning("Empty text for markdown splitting")
            return []

        logger.debug(f"Splitting markdown text of length {len(text)} characters")
        
        # Extract metadata from kwargs if provided
        base_metadata = kwargs.get("metadata", {})
        
        # MarkdownHeaderTextSplitter.split_text returns Documents with header metadata
        split_docs = self._splitter.split_text(text)
        
        # Merge base metadata with header metadata
        result = []
        for doc in split_docs:
            # Combine base metadata with the header metadata from splitting
            combined_metadata = base_metadata.copy()
            if doc.metadata:
                combined_metadata.update(doc.metadata)
            
            result.append(Document(
                page_content=doc.page_content,
                metadata=combined_metadata
            ))
        
        logger.debug(f"Created {len(result)} chunks from markdown text")
        
        return result
