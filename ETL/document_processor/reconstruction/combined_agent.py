# ETL.document_processor/reconstruction/combined_agent.py

from __future__ import annotations
from typing import Optional

from langchain_openai import AzureChatOpenAI

from ETL.document_processor.reconstruction.summary_agent import SummaryAgent
from ETL.document_processor.reconstruction.iterative_agent import IterativeReconstructionAgent
from ETL.document_processor.base.models import ProcessingConfig, RAGEntry

import logging

logger = logging.getLogger(__name__)


class CombinedReconstructionAgent(SummaryAgent, IterativeReconstructionAgent):
    """
    Agent combining summary augmentation and iterative reconstruction.
    
    First adds document summary to chunks, then improves each chunk iteratively.
    """
    
    def __init__(self, llm: AzureChatOpenAI, config: ProcessingConfig):
        # Initialize both parent classes
        SummaryAgent.__init__(self, llm, config)
        IterativeReconstructionAgent.__init__(self, llm, config)
    
    def reconstruct_chunks(
        self,
        chunks: list[RAGEntry],
        original_content: str,
        **kwargs
    ) -> list[RAGEntry]:
        """Apply both summary augmentation and iterative improvement."""
        try:
            print("I am in CombinedReconstructionAgent")
            # Step 1: Add document summary to chunks
            logger.info("Step 1: Adding document summary to chunks")
            chunks = SummaryAgent.reconstruct_chunks(
                self,
                chunks,
                original_content,
                **kwargs
            )
            
            # Step 2: Iteratively improve chunks
            logger.info("Step 2: Iteratively improving chunks")
            chunks = IterativeReconstructionAgent.reconstruct_chunks(
                self,
                chunks,
                original_content,
                **kwargs
            )
            
            return chunks
            
        except Exception as e:
            logger.error(f"Combined reconstruction failed: {e}", exc_info=True)
            return chunks
