"""Summary-based reconstruction agent."""

from __future__ import annotations
from typing import Optional

from langchain_openai import AzureChatOpenAI

from ETL.document_processor.reconstruction.base_agent import BaseReconstructionAgent
from ETL.document_processor.base.models import ProcessingConfig, RAGEntry

import logging

logger = logging.getLogger(__name__)


class SummaryAgent(BaseReconstructionAgent):
    """
    Agent that generates document summary and adds it to each chunk.
    
    This provides context to each chunk by prepending the document summary.
    Supports both document_intelligence and vision parser types.
    """
    
    def __init__(self, llm: AzureChatOpenAI, config: ProcessingConfig):
        super().__init__(llm, config)
        self.parser_type = config.parser_type
    
    def reconstruct_chunks(
        self,
        chunks: list[RAGEntry],
        original_content: str,
        **kwargs
    ) -> list[RAGEntry]:
        """Add summary context to each chunk."""
        try:
            # Early return for empty chunks
            if not chunks:
                logger.warning("No chunks to process")
                return chunks
            
            # Generate summary based on parser type
            summary = self._generate_summary(original_content, **kwargs)
            
            if not summary:
                logger.warning("No summary generated, returning chunks unchanged")
                return chunks
            
            # Augment chunks with summary
            chunks = self._augment_chunks(chunks, summary, **kwargs)
            
            logger.info(f"Augmented {len(chunks)} chunks with document summary")
            return chunks
            
        except Exception as e:
            logger.error(f"Summary reconstruction failed: {e}", exc_info=True)
            return chunks
    
    def _generate_summary(self, content: str, **kwargs) -> Optional[str]:
        """Generate summary based on parser type."""
        if self.parser_type == "document_intelligence":
            print("I am in generate summary DI")
            return self._generate_summary_header_resume(
                content,
                filename=kwargs.get("filename", 'document')
            )
        elif self.parser_type == "vision":
            print("I am in generate summary vision")
            return self._generate_summary_vision(content)
        else:
            logger.warning(
                f"Parser type '{self.parser_type}' not supported for summary augmentation"
            )
            return None
    
    def _augment_chunks(self, chunks: list[RAGEntry], summary: str, **kwargs) -> list[RAGEntry]:
        """Augment chunks with summary based on parser type."""
        if self.parser_type == "document_intelligence":
            for chunk in chunks:
                chunk.content = self._augment_chunk_with_summary_doc_intel(chunk.content, summary)
            return chunks
        elif self.parser_type == "vision":
            # Vision method returns a new deep-copied list
            # Extract filename from chunks metadata
            file_path = chunks[0].metadata.file_name if chunks else None
            return self._augment_chunks_summary_vision(chunks, summary, file_path)
        
        return chunks
    
    def _generate_summary_header_resume(self, content: str, filename: str) -> Optional[str]:
        """DI - Generate document summary using LLM."""
        try:
            # Import here to avoid circular dependency
            print("I am in generate summary DI - Header Resume")
            from ETL.tools.resumes import generate_document_resume
            return generate_document_resume(
                filename=filename,
                content=content,
                llm_model=self.llm
            )
        except Exception as e:
            logger.error(f"Resume Header - Summary generation failed: {e}")
            return None
    
    def _generate_summary_vision(self, content: str) -> Optional[str]:
        """Vision - Generate document summary using LLM."""
        try:
            print("I am in generate summary Vision - generate document summary stuff")
            # Import here to avoid circular dependency
            from ETL.tools.doc_etl_components import etl_components
            etl_obj = etl_components(file=None, llm_multimodal=self.llm)
            return etl_obj.generate_document_summary_stuff(content)
        
        except Exception as e:
            logger.error(f"Vision Summary generation failed: {e}")
            return None
    
    def _augment_chunk_with_summary_doc_intel(self, chunk_content: str, summary: str) -> str:
        """Augment chunk with summary for document intelligence parser."""
        if not summary:
            return chunk_content
        
        print("I am in Augment chunk with summary DI")
        
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
        
        - Uses deep copy (does not mutate the input list)
        - Derives filename via os.path.basename(file) (defaults to 'Not given')
        - Appends banner and str(summary) to each chunk.content
        - Matches the exact string formatting of append_chunks_fulldoc_summary
        
        Args:
            chunks: List of RAGEntry objects to augment
            summary: Consolidated document summary (will be cast to string)
            file: Optional file path used to derive the filename
            
        Returns:
            A deep-copied list of RAGEntry with augmented content
        """
        import os
        import copy
        
        print("I am in Augment chunk with summary VISION")
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
