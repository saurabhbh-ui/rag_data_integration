
from __future__ import annotations
from typing import Optional
from abc import ABC, abstractmethod

from langchain_openai import AzureChatOpenAI

from ETL.document_processor.base.interfaces import ReconstructionAgent
from ETL.document_processor.base.models import ProcessingConfig, RAGEntry

import logging

logger = logging.getLogger(__name__)


class BaseReconstructionAgent(ReconstructionAgent, ABC):
    """
    Base class providing common functionality for reconstruction agents.
    
    Provides LLM and config access, but doesn't force specific methods.
    Subclasses only need to implement reconstruct_chunks().
    """
    
    def __init__(self, llm: AzureChatOpenAI, config: ProcessingConfig):
        self.llm = llm
        self.config = config
    
    # Helper method (not abstract, not required)
    def _generate_summary(self, content: str, filename: str) -> Optional[str]:
        """
        Optional helper to generate summaries.
        Only used by implementations that need it.
        """
        raise NotImplementedError("This agent doesn't support summary generation")
    
    # Helper method (not abstract, not required)
    def _augment_chunk_with_summary_doc_intel(self, chunk_content: str, summary: str) -> str:
        """
        Augmentation helper for Document Intelligence/text parsers.
        Prepends a concise 'Document Context' header followed by the existing chunk content.
        """
        if not summary:
            return chunk_content
        return (
            f"Document Context:\n{summary}\n\n"
            f"Chunk Content:\n{chunk_content}"
        )
    

    def _augment_chunks_summary_vision(
        self,
        chunks: list[RAGEntry],
        summary: str,
        file: Optional[str] = None
    ) -> list[RAGEntry]:
        """
        Augment RAGEntry chunks with a consolidated summary in the exact same
        format and behavior as append_chunks_fulldoc_summary.
        
        - Derives filename via os.path.basename(file) (defaults to 'Not given')
        - Appends banner and str(summary) to each chunk.content
        - Matches the exact string formatting of append_chunks_fulldoc_summary
        
        Args:
            chunks: List of RAGEntry objects to augment
            summary: Consolidated document summary (will be cast to string)
            file: Optional file path used to derive the filename
            
        Returns:
            List[RAGEntry] with augmented content
        """
        import os
        import copy
        
        chunk_copy = copy.deepcopy(chunks)
        
        filename = os.path.basename(file) if file else 'Not given'
        doc_summary = summary
        
        for i in range(len(chunk_copy)):
            base_content = str(chunk_copy[i].content)
            entire_summary = (
                f"{base_content}\n\n---\n\n"
                f"### **Filename : {filename}** \n"
                f"### Consolidated summary / high-level overview of whole document given below: ###############\n\n"
                f"{str(doc_summary)}"
            )
            chunk_copy[i].content = entire_summary
        
        return chunk_copy
