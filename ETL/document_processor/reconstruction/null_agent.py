# ETL.document_processor/reconstruction/null_agent.py

"""Null reconstruction agent that returns chunks unchanged."""

from __future__ import annotations

from ETL.document_processor.base.interfaces import ReconstructionAgent
from ETL.document_processor.base.models import RAGEntry


class NullReconstructionAgent(ReconstructionAgent):
    """
    No-op reconstruction agent.
    
    Returns chunks unchanged - used when no reconstruction is needed.
    """
    
    def reconstruct_chunks(
        self,
        chunks: list[RAGEntry],
        original_content: str,
        **kwargs
    ) -> list[RAGEntry]:
        """Return chunks unchanged."""
        return chunks
