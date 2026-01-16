from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from pathlib import Path

if TYPE_CHECKING:
    from langchain.schema import Document
    from ETL.document_processor.base.models import RAGEntry

import logging

logger = logging.getLogger(__name__)


class Parser(ABC):
    """Abstract base class for document parsers."""
    
    @abstractmethod
    def parse(
        self,
        file_path: Path,
        file_metadata: dict,
        **kwargs
    ) -> tuple[str, int]:
        """
        Parse a document and return Markdown content.
        
        Returns:
            tuple: (Markdown content as string, number of unprocessed images)
        """
        raise NotImplementedError
    
    @abstractmethod
    def supports_file_type(self, file_extension: str) -> bool:
        """Check if this parser supports the given file type."""
        raise NotImplementedError


class Chunker(ABC):
    """Abstract base class for document chunkers."""
    
    @abstractmethod
    def split_text(self, text: str, **kwargs) -> list[Document]:
        """
        Split text into chunks.
        
        This is the standard method that all chunkers must implement.
        Returns a list of Document objects with page_content and metadata.
        """
        raise NotImplementedError
    

class ReconstructionAgent(ABC):
    """
    Abstract base class for document reconstruction/augmentation agents.
    
    - Only ONE abstract method: reconstruct_chunks()
    - HOW reconstruction is done is up to the implementation
    - Implementations can add their own helper methods
    """

    @abstractmethod
    def reconstruct_chunks(
        self,
        chunks: list[RAGEntry],
        original_content: str,
        **kwargs
    ) -> list[RAGEntry]:
        """
        Reconstruct/improve chunks in whatever way the agent sees fit.
        
        This is the ONLY required method. Implementations decide how:
        - NullAgent: Returns chunks unchanged
        - SummaryAgent: Adds document summary to chunks
        - IterativeAgent: Improves chunk quality iteratively
        - CombinedAgent: Does both summary + iterative
        - CustomAgent: Your own logic
        
        Args:
            chunks: List of chunk entries to improve
            original_content: Original full document content (for context)
            **kwargs: Additional parameters (e.g., filename)
            
        Returns:
            Improved list of chunks
        """
        raise NotImplementedError