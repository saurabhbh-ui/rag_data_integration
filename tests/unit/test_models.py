"""Unit tests for base models (RAGEntry, ProcessingConfig, etc.)."""

import pytest
from pydantic import ValidationError

from ETL.document_processor.base.models import (
    RAGMetadata,
    RAGEntry,
    ProcessingConfig,
    ChunkingStrategy,
    ParserType,
    ChunkAugmentMethod,
    ensure_str,
)


class TestEnsureStr:
    """Tests for ensure_str function."""

    def test_ensure_str_with_int(self):
        """Test that integers are converted to strings."""
        result = ensure_str(123)
        assert result == "123"
        assert isinstance(result, str)

    def test_ensure_str_with_str(self):
        """Test that strings remain strings."""
        result = ensure_str("already_string")
        assert result == "already_string"
        assert isinstance(result, str)

    def test_ensure_str_with_zero(self):
        """Test that zero is converted properly."""
        result = ensure_str(0)
        assert result == "0"


class TestRAGMetadata:
    """Tests for RAGMetadata model."""

    def test_create_valid_metadata(self):
        """Test creating valid metadata."""
        metadata = RAGMetadata(
            source="https://example.com/doc.pdf",
            file_name="document.pdf",
            file_type="pdf",
            document_title="Test Document",
            etag="abc123",
        )
        assert metadata.source == "https://example.com/doc.pdf"
        assert metadata.file_name == "document.pdf"
        assert metadata.file_type == "pdf"
        assert metadata.document_title == "Test Document"
        assert metadata.etag == "abc123"

    def test_metadata_with_defaults(self):
        """Test that default values are set correctly."""
        metadata = RAGMetadata(
            source="test",
            file_name="test.pdf",
            file_type="pdf",
            document_title="Test",
            etag="123",
        )
        assert metadata.keywords == [""]
        assert metadata.vector == []
        assert metadata.header_pages == {}
        assert metadata.page_number == ""

    def test_metadata_int_to_str_conversion(self):
        """Test that integer fields are converted to strings."""
        metadata = RAGMetadata(
            source="test",
            file_name="test.pdf",
            file_type="pdf",
            document_title="Test",
            etag="123",
            page_number=5,  # Integer input
            chunk_idx=10,  # Integer input
        )
        assert metadata.page_number == "5"
        assert metadata.chunk_idx == "10"
        assert isinstance(metadata.page_number, str)
        assert isinstance(metadata.chunk_idx, str)

    def test_metadata_forbids_extra_fields(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError):
            RAGMetadata(
                source="test",
                file_name="test.pdf",
                file_type="pdf",
                document_title="Test",
                etag="123",
                extra_field="not_allowed",  # Should raise error
            )

    def test_metadata_required_fields(self):
        """Test that required fields must be provided."""
        with pytest.raises(ValidationError):
            RAGMetadata()  # Missing required fields


class TestRAGEntry:
    """Tests for RAGEntry model."""

    def test_create_valid_entry(self):
        """Test creating a valid RAGEntry."""
        metadata = RAGMetadata(
            source="test",
            file_name="test.pdf",
            file_type="pdf",
            document_title="Test",
            etag="123",
        )
        entry = RAGEntry(
            content="Test content",
            metadata=metadata,
            file_id="file_123",
        )
        assert entry.content == "Test content"
        assert entry.file_id == "file_123"
        assert entry.metadata == metadata

    def test_entry_forbids_extra_fields(self):
        """Test that extra fields are not allowed."""
        metadata = RAGMetadata(
            source="test",
            file_name="test.pdf",
            file_type="pdf",
            document_title="Test",
            etag="123",
        )
        with pytest.raises(ValidationError):
            RAGEntry(
                content="Test",
                metadata=metadata,
                file_id="123",
                extra="not_allowed",
            )


class TestChunkingStrategy:
    """Tests for ChunkingStrategy enum."""

    def test_chunking_strategy_values(self):
        """Test that all chunking strategies are defined."""
        assert ChunkingStrategy.MARKDOWN == "markdown"
        assert ChunkingStrategy.RECURSIVE == "recursive"
        assert ChunkingStrategy.CHARACTER == "character"

    def test_chunking_strategy_from_string(self):
        """Test creating enum from string."""
        assert ChunkingStrategy("markdown") == ChunkingStrategy.MARKDOWN
        assert ChunkingStrategy("recursive") == ChunkingStrategy.RECURSIVE


class TestParserType:
    """Tests for ParserType enum."""

    def test_parser_type_values(self):
        """Test that all parser types are defined."""
        assert ParserType.DOCUMENT_INTELLIGENCE == "document_intelligence"
        assert ParserType.VISION == "vision"


class TestChunkAugmentMethod:
    """Tests for ChunkAugmentMethod enum."""

    def test_chunk_augment_method_values(self):
        """Test that all augment methods are defined."""
        assert ChunkAugmentMethod.BOTH == "both"
        assert ChunkAugmentMethod.APPEND_SUMMARY == "append_summary"
        assert ChunkAugmentMethod.CHUNK_RECONSTRUCTION == "chunk_reconstruction"
        assert ChunkAugmentMethod.NONE == "none"


class TestProcessingConfig:
    """Tests for ProcessingConfig model."""

    def test_create_default_config(self):
        """Test creating config with default values."""
        config = ProcessingConfig()
        assert config.parser_type == ParserType.DOCUMENT_INTELLIGENCE
        assert config.chunking_strategy == ChunkingStrategy.RECURSIVE
        assert config.chunk_size == 5000
        assert config.chunk_overlap == 500
        assert config.chunk_augment_method == ChunkAugmentMethod.NONE

    def test_create_custom_config(self):
        """Test creating config with custom values."""
        config = ProcessingConfig(
            parser_type=ParserType.VISION,
            chunking_strategy=ChunkingStrategy.MARKDOWN,
            chunk_size=1000,
            chunk_overlap=200,
        )
        assert config.parser_type == ParserType.VISION
        assert config.chunking_strategy == ChunkingStrategy.MARKDOWN
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200

    def test_chunk_augment_method_none(self):
        """Test that 'none' sets both flags to False."""
        config = ProcessingConfig(chunk_augment_method=ChunkAugmentMethod.NONE)
        assert config.append_summary_to_chunks is False
        assert config.use_iterative_reconstruction is False

    def test_chunk_augment_method_append_summary(self):
        """Test that 'append_summary' sets correct flags."""
        config = ProcessingConfig(
            chunk_augment_method=ChunkAugmentMethod.APPEND_SUMMARY
        )
        assert config.append_summary_to_chunks is True
        assert config.use_iterative_reconstruction is False

    def test_chunk_augment_method_chunk_reconstruction(self):
        """Test that 'chunk_reconstruction' sets correct flags."""
        config = ProcessingConfig(
            chunk_augment_method=ChunkAugmentMethod.CHUNK_RECONSTRUCTION
        )
        assert config.append_summary_to_chunks is False
        assert config.use_iterative_reconstruction is True

    def test_chunk_augment_method_both(self):
        """Test that 'both' sets both flags to True."""
        config = ProcessingConfig(chunk_augment_method=ChunkAugmentMethod.BOTH)
        assert config.append_summary_to_chunks is True
        assert config.use_iterative_reconstruction is True

    def test_chunk_size_validation(self):
        """Test that chunk_size must be greater than 0."""
        with pytest.raises(ValidationError):
            ProcessingConfig(chunk_size=0)

        with pytest.raises(ValidationError):
            ProcessingConfig(chunk_size=-100)

    def test_chunk_overlap_validation(self):
        """Test that chunk_overlap must be >= 0."""
        config = ProcessingConfig(chunk_overlap=0)  # Should work
        assert config.chunk_overlap == 0

        with pytest.raises(ValidationError):
            ProcessingConfig(chunk_overlap=-1)

    def test_config_with_string_enum_values(self):
        """Test that string values are converted to enums."""
        config = ProcessingConfig(
            parser_type="vision",
            chunking_strategy="character",
            chunk_augment_method="both",
        )
        # Enums should be converted due to use_enum_values=True
        assert config.parser_type == "vision"
        assert config.chunking_strategy == "character"
        assert config.chunk_augment_method == "both"

    def test_config_markdown_headers_default(self):
        """Test default markdown headers."""
        config = ProcessingConfig()
        assert config.markdown_headers == [("#", "h1"), ("##", "h2"), ("###", "h3")]

    def test_config_separators_default(self):
        """Test default separators."""
        config = ProcessingConfig()
        assert config.separators is None

    def test_document_page_stitching_default(self):
        """Test document_page_stitching default value."""
        config = ProcessingConfig()
        assert config.document_page_stitching is False

    def test_config_with_all_parameters(self):
        """Test creating config with all parameters."""
        config = ProcessingConfig(
            parser_type=ParserType.VISION,
            chunking_strategy=ChunkingStrategy.MARKDOWN,
            chunk_size=1000,
            chunk_overlap=100,
            markdown_headers=[("#", "h1")],
            separators=["\\n\\n", "\\n"],
            document_page_stitching=True,
            chunk_augment_method=ChunkAugmentMethod.BOTH,
        )
        assert config.parser_type == "vision"
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 100
        assert config.markdown_headers == [("#", "h1")]
        assert config.separators == ["\\n\\n", "\\n"]
        assert config.document_page_stitching is True
        assert config.append_summary_to_chunks is True
        assert config.use_iterative_reconstruction is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
