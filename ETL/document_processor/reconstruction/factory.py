# ETL.document_processor/reconstruction/factory.py

"""
Factory for creating reconstruction agent instances.
"""

from __future__ import annotations

from langchain_openai import AzureChatOpenAI

from ETL.document_processor.base.interfaces import ReconstructionAgent
from ETL.document_processor.base.models import ProcessingConfig
from ETL.document_processor.reconstruction.summary_agent import SummaryAgent
from ETL.document_processor.reconstruction.iterative_agent import IterativeReconstructionAgent
from ETL.document_processor.reconstruction.combined_agent import CombinedReconstructionAgent
from ETL.document_processor.reconstruction.null_agent import NullReconstructionAgent

import logging

logger = logging.getLogger(__name__)


class ReconstructionAgentFactory:
    """Factory for creating reconstruction agent instances."""
    
    @staticmethod
    def create_agent(config: ProcessingConfig, llm: AzureChatOpenAI) -> ReconstructionAgent:
        """
        Create appropriate reconstruction agent based on config.
        
        Args:
            config: Processing configuration
            llm: Azure ChatOpenAI instance
            
        Returns:
            ReconstructionAgent instance
        """
        if config.append_summary_to_chunks and config.use_iterative_reconstruction:
            logger.info("Creating CombinedReconstructionAgent")
            return CombinedReconstructionAgent(llm, config)
        
        elif config.append_summary_to_chunks:
            logger.info("Creating SummaryAgent")
            return SummaryAgent(llm, config)
        
        elif config.use_iterative_reconstruction:
            logger.info("Creating IterativeReconstructionAgent")
            return IterativeReconstructionAgent(llm, config)
        
        else:
            logger.info("Creating NullReconstructionAgent (no reconstruction)")
            return NullReconstructionAgent()
    
    @staticmethod
    def create_agent_by_type(
        agent_type: str,
        llm: AzureChatOpenAI,
        config: ProcessingConfig
    ) -> ReconstructionAgent:
        """
        Create agent by explicit type name.
        
        Args:
            agent_type: One of 'summary', 'iterative', 'combined', 'null'
            llm: Azure ChatOpenAI instance
            config: Processing configuration
            
        Returns:
            ReconstructionAgent instance
            
        Raises:
            ValueError: If agent_type is unknown
        """
        agent_type = agent_type.lower()
        
        if agent_type == "summary":
            return SummaryAgent(llm, config)
        elif agent_type == "iterative":
            return IterativeReconstructionAgent(llm, config)
        elif agent_type == "combined":
            return CombinedReconstructionAgent(llm, config)
        elif agent_type == "null":
            return NullReconstructionAgent()
        else:
            raise ValueError(
                f"Unknown agent type '{agent_type}'. "
                f"Supported: 'summary', 'iterative', 'combined', 'null'"
            )
