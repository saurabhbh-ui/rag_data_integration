"""Pydantic models."""

from __future__ import annotations

from typing import Annotated, Optional
from enum import Enum

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def ensure_str(value: int) -> str:
    """Force the value to be a string.

    Weaviate DB wants them to be strings.
    """
    return str(value) if isinstance(value, int) else value


class RAGMetadata(BaseModel):
    """Model representing the RAG metadata"""
    
    # Core required fields
    source: str = ""
    file_name: str = ""
    document_title: str = ""
    
    # Optional fields with validation
    keywords: list[str] = Field(default_factory=list)
    chunk_idx: Annotated[str, BeforeValidator(ensure_str)] = ""
    page_number: Annotated[str, BeforeValidator(ensure_str)] = ""

    model_config = ConfigDict(extra="allow")


class RAGEntry(BaseModel):
    """Model representing an entry in the Meeting Services Database (MSDB)."""
    content: str
    metadata: RAGMetadata
    file_id: str

    model_config = ConfigDict(extra="forbid")


class complete_doc(BaseModel):
    complete_doc: str = Field(default=None, description='complete document in markdown format')





# ===========================================
# CONFIGURATION MODELS
# ===========================================

class ChunkingStrategy(str, Enum):
    """Supported chunking strategies."""
    MARKDOWN = "markdown"
    RECURSIVE = "recursive"
    CHARACTER = "character"


class ParserType(str, Enum):
    """Supported parser types."""
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    VISION = "vision"


class ChunkAugmentMethod(str, Enum):
    """Supported chunk summary methods."""
    BOTH = "both"
    APPEND_SUMMARY = "append_summary"
    CHUNK_RECONSTRUCTION = "chunk_reconstruction"
    NONE = "none"


class ProcessingConfig(BaseModel):
    """Complete configuration for document processing."""
    
    # Parser configuration
    parser_type: ParserType = Field(
        default=ParserType.DOCUMENT_INTELLIGENCE,
        description="Parser type for PDF processing"
    )

    # Chunking configuration
    chunking_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.RECURSIVE,
        description="Strategy for chunking documents"
    )
    chunk_size: int = Field(default=5000, gt=0, description="Size of chunks")
    chunk_overlap: int = Field(default=500, ge=0, description="Overlap between chunks")
    
    # Markdown-specific settings
    markdown_headers: list[tuple[str, str]] = Field(
        default=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        description="Headers for markdown splitting"
    )
    
    # Recursive-specific settings
    separators: Optional[list[str]] = Field(
        default=None,
        description="Separators for recursive chunking"
    )
    
    document_page_stitching: bool = Field(
        default=False,
        description="Process PDF pages individually-complete the document is any disconnectt due to pagewise processing."
    )


    # Chunk summary method configuration
    chunk_augment_method: ChunkAugmentMethod = Field(
        default=ChunkAugmentMethod.NONE,
        description="Method for chunk summarization: 'both', 'append_summary', 'chunk_reconstruction', or 'none'"
    )
    
    # Summary configuration
    append_summary_to_chunks: bool = Field(
        default=False,
        description="Append document summary to each chunk"
    )
    

    # Iterative reconstruction configuration
    use_iterative_reconstruction: bool = Field(
        default=False,
        description="Enable iterative chunk reconstruction for improved results"
    )

    model_config = ConfigDict(use_enum_values=True)
    

    def __init__(self, **data):
        """Initialize ProcessingConfig and apply chunk_augment_method logic."""
        super().__init__(**data)
        
        # Apply logic based on chunk_augment_method
        method = self.chunk_augment_method
        
        if method == ChunkAugmentMethod.BOTH or method == "both":
            self.append_summary_to_chunks = True
            self.use_iterative_reconstruction = True
        elif method == ChunkAugmentMethod.APPEND_SUMMARY or method == "append_summary":
            self.append_summary_to_chunks = True
            self.use_iterative_reconstruction = False
        elif method == ChunkAugmentMethod.CHUNK_RECONSTRUCTION or method == "chunk_reconstruction":
            self.append_summary_to_chunks = False
            self.use_iterative_reconstruction = True
        elif method == ChunkAugmentMethod.NONE or method == "none" or method is None:
            self.append_summary_to_chunks = False
            self.use_iterative_reconstruction = False