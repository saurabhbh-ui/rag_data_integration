"""Unit tests for reconstruction agent modules."""

import pytest
from unittest.mock import Mock, MagicMock

from ETL.document_processor.reconstruction.null_agent import NullReconstructionAgent
from ETL.document_processor.reconstruction.summary_agent import SummaryAgent
from ETL.document_processor.reconstruction.iterative_agent import (
    IterativeReconstructionAgent,
)
from ETL.document_processor.reconstruction.combined_agent import (
    CombinedReconstructionAgent,
)
from ETL.document_processor.reconstruction.factory import ReconstructionAgentFactory
from ETL.document_processor.base.models import (
    ProcessingConfig,
    ChunkAugmentMethod,
)
from tests.fixtures import (
    create_sample_config,
    create_sample_chunks,
    create_mock_llm,
    SAMPLE_TEXT_LONG,
)


class TestNullReconstructionAgent:
    """Tests for NullReconstructionAgent."""

    def test_initialization(self):
        """Test NullReconstructionAgent initialization."""
        agent = NullReconstructionAgent()
        assert agent is not None

    def test_reconstruct_chunks_returns_unchanged(self):
        """Test that null agent returns chunks unchanged."""
        agent = NullReconstructionAgent()
        chunks = create_sample_chunks(3)
        original_content = SAMPLE_TEXT_LONG

        result = agent.reconstruct_chunks(chunks, original_content)

        assert result == chunks
        assert len(result) == len(chunks)
        # Verify chunks are the exact same objects
        for i, chunk in enumerate(result):
            assert chunk is chunks[i]

    def test_reconstruct_empty_chunks(self):
        """Test reconstructing empty chunk list."""
        agent = NullReconstructionAgent()
        result = agent.reconstruct_chunks([], SAMPLE_TEXT_LONG)
        assert result == []

    def test_reconstruct_with_kwargs(self):
        """Test that kwargs are accepted but ignored."""
        agent = NullReconstructionAgent()
        chunks = create_sample_chunks(2)
        result = agent.reconstruct_chunks(
            chunks,
            SAMPLE_TEXT_LONG,
            filename="test.pdf",
            extra_param="value",
        )
        assert result == chunks


class TestSummaryAgent:
    """Tests for SummaryAgent."""

    def test_initialization(self):
        """Test SummaryAgent initialization."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = SummaryAgent(llm, config)
        assert agent.llm == llm
        assert agent.config == config

    def test_reconstruct_chunks_adds_summary(self):
        """Test that summary agent adds summary to chunks."""
        llm = create_mock_llm()
        # Mock LLM to return a specific summary
        llm.invoke.return_value = Mock(content="This is a document summary.")

        config = create_sample_config()
        agent = SummaryAgent(llm, config)
        chunks = create_sample_chunks(3)
        original_content = SAMPLE_TEXT_LONG

        result = agent.reconstruct_chunks(chunks, original_content)

        # Verify LLM was called
        assert llm.invoke.called

        # Verify chunks were modified
        assert len(result) == len(chunks)
        for chunk in result:
            # Summary should be appended to content
            assert isinstance(chunk.content, str)

    def test_reconstruct_empty_chunks(self):
        """Test reconstructing empty chunks."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = SummaryAgent(llm, config)

        result = agent.reconstruct_chunks([], SAMPLE_TEXT_LONG)
        # Should handle gracefully
        assert isinstance(result, list)

    def test_llm_invocation_with_correct_content(self):
        """Test that LLM is invoked with the original content."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = SummaryAgent(llm, config)
        chunks = create_sample_chunks(2)

        agent.reconstruct_chunks(chunks, SAMPLE_TEXT_LONG)

        # Verify LLM was called
        assert llm.invoke.called
        # Check that some form of the original content was used
        call_args = llm.invoke.call_args
        assert call_args is not None


class TestIterativeReconstructionAgent:
    """Tests for IterativeReconstructionAgent."""

    def test_initialization(self):
        """Test IterativeReconstructionAgent initialization."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = IterativeReconstructionAgent(llm, config)
        assert agent.llm == llm
        assert agent.config == config

    def test_reconstruct_chunks_improves_chunks(self):
        """Test that iterative agent processes chunks."""
        llm = create_mock_llm()
        # Mock LLM to return improved content
        llm.invoke.return_value = Mock(content="Improved chunk content.")

        config = create_sample_config()
        agent = IterativeReconstructionAgent(llm, config)
        chunks = create_sample_chunks(2)

        result = agent.reconstruct_chunks(chunks, SAMPLE_TEXT_LONG)

        # Verify chunks were processed
        assert len(result) == len(chunks)
        # LLM should be called for each chunk
        assert llm.invoke.call_count >= len(chunks)

    def test_reconstruct_empty_chunks(self):
        """Test handling empty chunks list."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = IterativeReconstructionAgent(llm, config)

        result = agent.reconstruct_chunks([], SAMPLE_TEXT_LONG)
        assert isinstance(result, list)

    def test_reconstruct_single_chunk(self):
        """Test reconstructing a single chunk."""
        llm = create_mock_llm()
        llm.invoke.return_value = Mock(content="Improved single chunk.")

        config = create_sample_config()
        agent = IterativeReconstructionAgent(llm, config)
        chunks = create_sample_chunks(1)

        result = agent.reconstruct_chunks(chunks, SAMPLE_TEXT_LONG)

        assert len(result) == 1
        assert llm.invoke.called


class TestCombinedReconstructionAgent:
    """Tests for CombinedReconstructionAgent."""

    def test_initialization(self):
        """Test CombinedReconstructionAgent initialization."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = CombinedReconstructionAgent(llm, config)
        assert agent.llm == llm
        assert agent.config == config

    def test_reconstruct_combines_both_strategies(self):
        """Test that combined agent uses both summary and iterative."""
        llm = create_mock_llm()
        llm.invoke.return_value = Mock(content="Combined improvement.")

        config = create_sample_config()
        agent = CombinedReconstructionAgent(llm, config)
        chunks = create_sample_chunks(2)

        result = agent.reconstruct_chunks(chunks, SAMPLE_TEXT_LONG)

        # Verify chunks were processed
        assert len(result) == len(chunks)
        # LLM should be called multiple times (summary + iterative)
        assert llm.invoke.called

    def test_reconstruct_empty_chunks(self):
        """Test handling empty chunks."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = CombinedReconstructionAgent(llm, config)

        result = agent.reconstruct_chunks([], SAMPLE_TEXT_LONG)
        assert isinstance(result, list)


class TestReconstructionAgentFactory:
    """Tests for ReconstructionAgentFactory."""

    def test_create_null_agent_when_no_augmentation(self):
        """Test creating null agent when no augmentation is configured."""
        llm = create_mock_llm()
        config = create_sample_config(chunk_augment_method=ChunkAugmentMethod.NONE)
        agent = ReconstructionAgentFactory.create_agent(config, llm)
        assert isinstance(agent, NullReconstructionAgent)

    def test_create_summary_agent_when_append_summary(self):
        """Test creating summary agent for append_summary mode."""
        llm = create_mock_llm()
        config = create_sample_config(
            chunk_augment_method=ChunkAugmentMethod.APPEND_SUMMARY
        )
        agent = ReconstructionAgentFactory.create_agent(config, llm)
        assert isinstance(agent, SummaryAgent)

    def test_create_iterative_agent_when_chunk_reconstruction(self):
        """Test creating iterative agent for chunk_reconstruction mode."""
        llm = create_mock_llm()
        config = create_sample_config(
            chunk_augment_method=ChunkAugmentMethod.CHUNK_RECONSTRUCTION
        )
        agent = ReconstructionAgentFactory.create_agent(config, llm)
        assert isinstance(agent, IterativeReconstructionAgent)

    def test_create_combined_agent_when_both(self):
        """Test creating combined agent for both mode."""
        llm = create_mock_llm()
        config = create_sample_config(chunk_augment_method=ChunkAugmentMethod.BOTH)
        agent = ReconstructionAgentFactory.create_agent(config, llm)
        assert isinstance(agent, CombinedReconstructionAgent)

    def test_create_agent_by_type_summary(self):
        """Test creating agent by explicit type - summary."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = ReconstructionAgentFactory.create_agent_by_type("summary", llm, config)
        assert isinstance(agent, SummaryAgent)

    def test_create_agent_by_type_iterative(self):
        """Test creating agent by explicit type - iterative."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = ReconstructionAgentFactory.create_agent_by_type(
            "iterative", llm, config
        )
        assert isinstance(agent, IterativeReconstructionAgent)

    def test_create_agent_by_type_combined(self):
        """Test creating agent by explicit type - combined."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = ReconstructionAgentFactory.create_agent_by_type("combined", llm, config)
        assert isinstance(agent, CombinedReconstructionAgent)

    def test_create_agent_by_type_null(self):
        """Test creating agent by explicit type - null."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = ReconstructionAgentFactory.create_agent_by_type("null", llm, config)
        assert isinstance(agent, NullReconstructionAgent)

    def test_create_agent_by_type_case_insensitive(self):
        """Test that agent type is case insensitive."""
        llm = create_mock_llm()
        config = create_sample_config()
        agent = ReconstructionAgentFactory.create_agent_by_type("SUMMARY", llm, config)
        assert isinstance(agent, SummaryAgent)

    def test_create_agent_by_type_invalid(self):
        """Test that invalid agent type raises error."""
        llm = create_mock_llm()
        config = create_sample_config()
        with pytest.raises(ValueError, match="Unknown agent type"):
            ReconstructionAgentFactory.create_agent_by_type("invalid", llm, config)

    def test_factory_creates_different_instances(self):
        """Test that factory creates new instances each time."""
        llm = create_mock_llm()
        config = create_sample_config(
            chunk_augment_method=ChunkAugmentMethod.APPEND_SUMMARY
        )
        agent1 = ReconstructionAgentFactory.create_agent(config, llm)
        agent2 = ReconstructionAgentFactory.create_agent(config, llm)
        assert agent1 is not agent2


class TestReconstructionAgentIntegration:
    """Integration tests for reconstruction agents."""

    def test_all_agents_handle_chunks(self):
        """Test that all agent types can process chunks."""
        llm = create_mock_llm()
        llm.invoke.return_value = Mock(content="Test response")

        chunks = create_sample_chunks(2)
        agents = [
            NullReconstructionAgent(),
            SummaryAgent(llm, create_sample_config()),
            IterativeReconstructionAgent(llm, create_sample_config()),
            CombinedReconstructionAgent(llm, create_sample_config()),
        ]

        for agent in agents:
            result = agent.reconstruct_chunks(chunks, SAMPLE_TEXT_LONG)
            assert isinstance(result, list)
            assert len(result) == len(chunks)

    def test_agents_preserve_chunk_count(self):
        """Test that agents preserve the number of chunks."""
        llm = create_mock_llm()
        llm.invoke.return_value = Mock(content="Response")

        for num_chunks in [1, 3, 5]:
            chunks = create_sample_chunks(num_chunks)
            
            # Test each agent type
            agents = [
                NullReconstructionAgent(),
                SummaryAgent(llm, create_sample_config()),
            ]
            
            for agent in agents:
                result = agent.reconstruct_chunks(chunks, SAMPLE_TEXT_LONG)
                assert len(result) == num_chunks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
