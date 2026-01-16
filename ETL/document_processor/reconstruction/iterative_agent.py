# ETL.document_processor/reconstruction/iterative_agent.py

from __future__ import annotations

from langchain_openai import AzureChatOpenAI

from ETL.document_processor.reconstruction.base_agent import BaseReconstructionAgent
from ETL.document_processor.base.models import ProcessingConfig, RAGEntry

import logging

logger = logging.getLogger(__name__)


class IterativeReconstructionAgent(BaseReconstructionAgent):
    """
    Agent that iteratively improves chunk quality.
    
    Uses ChunkImprover to enhance each chunk based on the full document context.
    """
    
    def __init__(self, llm: AzureChatOpenAI, config: ProcessingConfig):
        super().__init__(llm, config)
        
        # Import here to avoid issues if module not available
        try:
            from ETL.tools.rag_chunking_agent.chunk_improver import ChunkImprover
            self.improver = ChunkImprover(llm=self.llm)
        except ImportError as e:
            logger.warning(f"ChunkImprover not available: {e}")
            self.improver = None
    
    def reconstruct_chunks(
        self,
        chunks: list[RAGEntry],
        original_content: str,
        **kwargs
    ) -> list[RAGEntry]:
        """Iteratively improve each chunk."""
        if not self.improver:
            logger.warning("ChunkImprover not available, returning chunks unchanged")
            return chunks
        
        try:
            print("I am in iterative improvement agent")
            for idx, chunk in enumerate(chunks, 1):
                result = self.improver.improve_chunk(
                    document=original_content or "",
                    chunk=chunk.content,
                    return_only_result=False
                )
                chunk.content = result.improved_chunk
                logger.info(f"[Chunk {idx}/{len(chunks)}] quality score: {result.quality_score:.2f}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Iterative reconstruction failed: {e}", exc_info=True)
            return chunks
