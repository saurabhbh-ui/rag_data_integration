"""Test fixtures and mock data for ETL pipeline tests."""

from pathlib import Path
from unittest.mock import Mock
from typing import Any, Dict

from ETL.document_processor.base.models import (
    RAGEntry,
    RAGMetadata,
    ProcessingConfig,
    ChunkingStrategy,
    ParserType,
    ChunkAugmentMethod,
)


# Sample text content for testing
SAMPLE_TEXT_SHORT = "This is a short test document."

SAMPLE_TEXT_MEDIUM = """# Main Title

This is a test document with multiple paragraphs.

## Section 1

This is the first section with some content.
It has multiple lines of text.

## Section 2

This is the second section.
It also contains some information.

### Subsection 2.1

More detailed content here.
"""

SAMPLE_TEXT_LONG = """# Document Title

## Introduction

This is a comprehensive test document that will be used for testing chunking and parsing.
It contains multiple sections and subsections to simulate real-world documents.

## Chapter 1: Background

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor 
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

### Section 1.1: Details

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu 
fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in 
culpa qui officia deserunt mollit anim id est laborum.

### Section 1.2: More Details

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque 
laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi 
architecto beatae vitae dicta sunt explicabo.

## Chapter 2: Analysis

Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia 
consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.

## Conclusion

This concludes our test document with sufficient content for chunking tests.
"""


def create_sample_metadata(
    source: str = "test_source",
    file_name: str = "test_file.pdf",
    file_type: str = "pdf",
    document_title: str = "Test Document",
) -> RAGMetadata:
    """Create sample RAGMetadata for testing."""
    return RAGMetadata(
        source=source,
        file_name=file_name,
        file_type=file_type,
        document_title=document_title,
        etag="test_etag_123",
        keywords=["test", "document"],
        vector=[],
        header_pages={},
        page_number="1",
        h1_name="",
        h1_idx="",
        h2_name="",
        h2_idx="",
        h3_name="",
        h3_idx="",
        chunk_idx="0",
        table_resume="",
    )


def create_sample_entry(
    content: str = "Test content",
    file_id: str = "test_file_id_001",
    **metadata_kwargs,
) -> RAGEntry:
    """Create sample RAGEntry for testing."""
    metadata = create_sample_metadata(**metadata_kwargs)
    return RAGEntry(
        content=content,
        metadata=metadata,
        file_id=file_id,
    )


def create_sample_config(
    parser_type: ParserType = ParserType.DOCUMENT_INTELLIGENCE,
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
    chunk_augment_method: ChunkAugmentMethod = ChunkAugmentMethod.NONE,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    **kwargs,
) -> ProcessingConfig:
    """Create sample ProcessingConfig for testing."""
    return ProcessingConfig(
        parser_type=parser_type,
        chunking_strategy=chunking_strategy,
        chunk_augment_method=chunk_augment_method,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs,
    )


def create_mock_llm() -> Mock:
    """Create a mock LLM for testing."""
    mock_llm = Mock()
    mock_llm.invoke = Mock(return_value=Mock(content="Mock LLM response"))
    return mock_llm


def create_mock_embeddings() -> Mock:
    """Create mock embeddings for testing."""
    mock_embeddings = Mock()
    mock_embeddings.embed_documents = Mock(return_value=[[0.1] * 768])
    mock_embeddings.embed_query = Mock(return_value=[0.1] * 768)
    return mock_embeddings


def create_temp_file(tmp_path: Path, filename: str, content: str) -> Path:
    """Create a temporary file with content."""
    file_path = tmp_path / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


# Sample file metadata
SAMPLE_FILE_METADATA = {
    "source": "https://example.com/document.pdf",
    "file_name": "document.pdf",
    "file_type": "pdf",
    "document_title": "Sample Document",
    "etag": "abc123",
}


# Sample chunks for testing reconstruction
def create_sample_chunks(num_chunks: int = 3) -> list[RAGEntry]:
    """Create sample chunks for testing."""
    chunks = []
    for i in range(num_chunks):
        metadata = create_sample_metadata()
        metadata.chunk_idx = str(i)
        chunks.append(
            RAGEntry(
                content=f"This is chunk {i} content with some text.",
                metadata=metadata,
                file_id=f"test_file_{i}",
            )
        )
    return chunks
