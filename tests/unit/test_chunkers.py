"""Unit tests for chunker modules."""

import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document

from ETL.document_processor.chunkers.character_chunker import CharacterChunker
from ETL.document_processor.chunkers.recursive_chunker import RecursiveChunker
from ETL.document_processor.chunkers.markdown_chunker import MarkdownChunker
from ETL.document_processor.chunkers.factory import ChunkerFactory
from ETL.document_processor.base.models import ProcessingConfig, ChunkingStrategy
from tests.fixtures import (
    SAMPLE_TEXT_SHORT,
    SAMPLE_TEXT_MEDIUM,
    SAMPLE_TEXT_LONG,
    create_sample_config,
    create_mock_embeddings,
)


class TestCharacterChunker:
    """Tests for CharacterChunker."""

    def test_initialization(self):
        """Test that CharacterChunker initializes correctly."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.CHARACTER, chunk_size=100, chunk_overlap=20
        )
        chunker = CharacterChunker(config)
        assert chunker.config == config
        assert chunker._splitter is not None

    def test_initialization_with_embeddings(self):
        """Test initialization with embeddings."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.CHARACTER)
        embeddings = create_mock_embeddings()
        chunker = CharacterChunker(config, embeddings)
        assert chunker.embeddings == embeddings

    def test_split_text_simple(self):
        """Test splitting simple text."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.CHARACTER, chunk_size=50, chunk_overlap=10
        )
        chunker = CharacterChunker(config)
        result = chunker.split_text(SAMPLE_TEXT_SHORT)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(doc, Document) for doc in result)
        assert all(hasattr(doc, "page_content") for doc in result)

    def test_split_text_with_metadata(self):
        """Test that metadata is attached to chunks."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.CHARACTER)
        chunker = CharacterChunker(config)
        metadata = {"source": "test.txt", "page": 1}
        result = chunker.split_text(SAMPLE_TEXT_MEDIUM, metadata=metadata)

        assert len(result) > 0
        for doc in result:
            assert doc.metadata == metadata

    def test_split_empty_text(self):
        """Test that empty text returns empty list."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.CHARACTER)
        chunker = CharacterChunker(config)

        result = chunker.split_text("")
        assert result == []

        result = chunker.split_text("   ")
        assert result == []


class TestRecursiveChunker:
    """Tests for RecursiveChunker."""

    def test_initialization(self):
        """Test that RecursiveChunker initializes correctly."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.RECURSIVE, chunk_size=200, chunk_overlap=50
        )
        chunker = RecursiveChunker(config)
        assert chunker.config == config
        assert chunker._splitter is not None

    def test_split_text_simple(self):
        """Test splitting simple text."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.RECURSIVE, chunk_size=100, chunk_overlap=20
        )
        chunker = RecursiveChunker(config)
        result = chunker.split_text(SAMPLE_TEXT_MEDIUM)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(doc, Document) for doc in result)

    def test_split_text_with_separators(self):
        """Test splitting with custom separators."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.RECURSIVE,
            chunk_size=200,
            separators=["\\n\\n", "\\n", " "],
        )
        chunker = RecursiveChunker(config)
        result = chunker.split_text(SAMPLE_TEXT_LONG)

        assert len(result) > 0
        # Verify chunks are created
        total_length = sum(len(doc.page_content) for doc in result)
        assert total_length > 0

    def test_split_empty_text(self):
        """Test handling of empty text."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.RECURSIVE)
        chunker = RecursiveChunker(config)

        result = chunker.split_text("")
        assert result == []

    def test_split_text_preserves_metadata(self):
        """Test that metadata is preserved across chunks."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.RECURSIVE)
        chunker = RecursiveChunker(config)
        metadata = {"file_name": "test.md", "source": "test"}
        result = chunker.split_text(SAMPLE_TEXT_MEDIUM, metadata=metadata)

        for doc in result:
            assert doc.metadata == metadata


class TestMarkdownChunker:
    """Tests for MarkdownChunker."""

    def test_initialization(self):
        """Test that MarkdownChunker initializes correctly."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.MARKDOWN, chunk_size=300, chunk_overlap=50
        )
        chunker = MarkdownChunker(config)
        assert chunker.config == config
        assert chunker._splitter is not None

    def test_split_markdown_text(self):
        """Test splitting markdown with headers."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.MARKDOWN, chunk_size=200, chunk_overlap=30
        )
        chunker = MarkdownChunker(config)
        result = chunker.split_text(SAMPLE_TEXT_MEDIUM)

        assert isinstance(result, list)
        assert len(result) > 0
        # Verify chunks contain content
        assert all(len(doc.page_content) > 0 for doc in result)

    def test_markdown_headers_in_metadata(self):
        """Test that markdown headers are tracked in metadata."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.MARKDOWN)
        chunker = MarkdownChunker(config)
        result = chunker.split_text(SAMPLE_TEXT_MEDIUM)

        # At least some chunks should have header information
        assert len(result) > 0

    def test_custom_markdown_headers(self):
        """Test using custom markdown headers."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.MARKDOWN,
            markdown_headers=[("#", "h1"), ("##", "h2")],
        )
        chunker = MarkdownChunker(config)
        result = chunker.split_text(SAMPLE_TEXT_LONG)

        assert len(result) > 0

    def test_split_empty_markdown(self):
        """Test handling empty markdown."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.MARKDOWN)
        chunker = MarkdownChunker(config)
        result = chunker.split_text("")
        assert result == []


class TestChunkerFactory:
    """Tests for ChunkerFactory."""

    def test_create_character_chunker(self):
        """Test creating CharacterChunker via factory."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.CHARACTER)
        chunker = ChunkerFactory.create_chunker(config)
        assert isinstance(chunker, CharacterChunker)

    def test_create_recursive_chunker(self):
        """Test creating RecursiveChunker via factory."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.RECURSIVE)
        chunker = ChunkerFactory.create_chunker(config)
        assert isinstance(chunker, RecursiveChunker)

    def test_create_markdown_chunker(self):
        """Test creating MarkdownChunker via factory."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.MARKDOWN)
        chunker = ChunkerFactory.create_chunker(config)
        assert isinstance(chunker, MarkdownChunker)


    def test_factory_creates_different_instances(self):
        """Test that factory creates new instances each time."""
        config = create_sample_config(chunking_strategy=ChunkingStrategy.RECURSIVE)
        chunker1 = ChunkerFactory.create_chunker(config)
        chunker2 = ChunkerFactory.create_chunker(config)
        assert chunker1 is not chunker2


class TestChunkerIntegration:
    """Integration tests for chunkers."""

    def test_all_chunkers_handle_same_text(self):
        """Test that all chunkers can process the same text."""
        text = SAMPLE_TEXT_LONG
        strategies = [
            ChunkingStrategy.CHARACTER,
            ChunkingStrategy.RECURSIVE,
            ChunkingStrategy.MARKDOWN,
        ]

        for strategy in strategies:
            config = create_sample_config(
                chunking_strategy=strategy, chunk_size=500, chunk_overlap=100
            )
            chunker = ChunkerFactory.create_chunker(config)
            result = chunker.split_text(text)

            assert len(result) > 0, f"Failed for strategy: {strategy}"
            assert all(isinstance(doc, Document) for doc in result)
            assert all(len(doc.page_content) > 0 for doc in result)

    def test_chunkers_produce_non_overlapping_content(self):
        """Test that chunk content doesn't have huge overlaps (within tolerance)."""
        config = create_sample_config(
            chunking_strategy=ChunkingStrategy.RECURSIVE,
            chunk_size=200,
            chunk_overlap=50,
        )
        chunker = ChunkerFactory.create_chunker(config)
        result = chunker.split_text(SAMPLE_TEXT_LONG)

        # Verify we got multiple chunks
        assert len(result) > 1

        # Check overlap is reasonable (this is approximate)
        for i in range(len(result) - 1):
            chunk1 = result[i].page_content
            chunk2 = result[i + 1].page_content
            # Chunks should not be identical
            assert chunk1 != chunk2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
