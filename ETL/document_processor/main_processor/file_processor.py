"""
Main File Processor Orchestrator
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import logging
from time import sleep

import weaviate
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from ETL.document_processor.base.models import RAGEntry, RAGMetadata, ProcessingConfig
from ETL.document_processor.utils.exceptions import ProcessingError, StorageError
from ETL.document_processor.parsers.factory import ParserFactory
from ETL.document_processor.chunkers.factory import ChunkerFactory
from ETL.document_processor.reconstruction.factory import ReconstructionAgentFactory
from ETL.document_processor.utils.keyword_generator import KeywordGenerator
from ETL.document_processor.utils.settings import (
    azure_openai_completion_settings,
    azure_openai_embedding_settings,
    document_intelligence_settings,
    weaviate_settings,
)

logger = logging.getLogger(__name__)


class FileProcessor:
    """Main orchestrator for document processing pipeline."""
    def __init__(self, weaviate_client: weaviate.WeaviateClient, config: Optional[ProcessingConfig] = None):
    #def __init__(self, config: Optional[ProcessingConfig] = None):
        self.weaviate_client = weaviate_client
        self.config = config or ProcessingConfig()

        try:
            self.collection = self.weaviate_client.collections.get(weaviate_settings.collection_name)
        except Exception as e:
            logger.error(f"Failed to get Weaviate collection: {e}")
            raise StorageError(f"Collection access failed: {e}") from e

        try:
            self._initialize_azure_components()
        except Exception as e:
            logger.error(f"Failed to initialize Azure components: {e}")
            raise ProcessingError(f"Azure initialization failed: {e}") from e

        try:
            self.chunker = ChunkerFactory.create_chunker(config=self.config, embeddings=self.embeddings)
            self.reconstruction_agent = ReconstructionAgentFactory.create_agent(config=self.config, llm=self.llm)
            self.keyword_generator = KeywordGenerator(llm=self.llm)
        except Exception as e:
            logger.error(f"Failed to initialize processors: {e}")
            raise ProcessingError(f"Processor initialization failed: {e}") from e

        logger.info(
            f"Initialized FileProcessor | Parser: {self.config.parser_type} | "
            f"Chunker: {self.config.chunking_strategy} | "
            f"append_summary={self.config.append_summary_to_chunks} | "
            f"iterative_reconstruction={self.config.use_iterative_reconstruction}"
        )

    def _initialize_azure_components(self):
        self.embeddings = AzureOpenAIEmbeddings(
            azure_deployment=azure_openai_embedding_settings.deployment,
            openai_api_version=azure_openai_embedding_settings.api_version,
            azure_endpoint=azure_openai_embedding_settings.endpoint,
            openai_api_key=azure_openai_embedding_settings.api_key,
            max_retries=3,
            retry_min_seconds=20,
            retry_max_seconds=60,
        )
        self.llm = AzureChatOpenAI(
            azure_endpoint=azure_openai_completion_settings.endpoint,
            azure_deployment=azure_openai_completion_settings.deployment,
            api_key=azure_openai_completion_settings.api_key,
            api_version=azure_openai_completion_settings.api_version,
            temperature=0.0,
            verbose=False,
            streaming=False,
            max_retries=3,
        )
        self.di_client = DocumentIntelligenceClient(
            endpoint=document_intelligence_settings.endpoint,
            credential=AzureKeyCredential(document_intelligence_settings.api_key),
            api_version="2024-07-31-preview",
        )

    def _choose_parser_type_for_extension(self, ext: str) -> str:
        """
        Choose parser type based on extension.
        - For pdf: use configured parser_type ('document_intelligence' or 'vision')
        - For others: map extension to dedicated parser type
        """
        ext = ext.lower()
        if ext == ".pdf":
            parser_type = self.config.parser_type
            return parser_type if isinstance(parser_type, str) else parser_type.value
        if ext in [".txt", ".text", ".md"]:
            return "text"
        if ext == ".docx":
            return "docx"
        if ext == ".aspx":
            return "aspx"
        if ext == ".xlsx":
            return "excel"
        return "text"

    def process_file(self, file_path: Path, file_metadata: dict) -> tuple[int, int]:
        try:
            logger.info(f"Processing file: {file_path.name} ({file_path.suffix})")

            file_type = file_path.suffix.lstrip(".").lower()
            parser_type = self._choose_parser_type_for_extension(file_path.suffix)

            parser = ParserFactory.get_parser(
                file_type=file_type,
                parser_type=parser_type,
                di_client=self.di_client,
                llm=self.llm,
                config=self.config
            )

            markdown_content, n_unprocessed_images = parser.parse(
                file_path=file_path,
                file_metadata=file_metadata
            )

            chunks = self.chunker.split_text(text=markdown_content, metadata={"source": str(file_path)})

            chunks_as_entries = self._convert_chunks_to_entries(
                chunks=chunks,
                file_path=file_path,
                file_metadata=file_metadata
            )

            # The agent internally decides what to do (summary, iterative, both, or nothing)
            if self.config.append_summary_to_chunks or self.config.use_iterative_reconstruction:
                logger.info("Reconstructing chunks...")
                chunks_as_entries = self.reconstruction_agent.reconstruct_chunks(
                    chunks=chunks_as_entries,
                    original_content=markdown_content,
                    filename=file_path.stem
                )

            if chunks_as_entries:
                self.store_chunks(chunks_as_entries)
                logger.info(f"Successfully processed {file_path.name}: {len(chunks_as_entries)} chunks stored")
            else:
                logger.warning(f"No chunks generated for {file_path.name}")

            return len(chunks_as_entries), n_unprocessed_images

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}", exc_info=True)
            raise ProcessingError(f"File processing failed for {file_path.name}: {e}") from e


    def _convert_chunks_to_entries(self, chunks: list, file_path: Path, file_metadata: dict) -> list[RAGEntry]:
        try:
            metadata = RAGMetadata(
                source=file_metadata.get("web_url", ""),
                file_name=file_path.name,
                file_type=file_path.suffix,
                etag=file_metadata.get("etag", ""),
                document_title=file_path.stem,
                header_pages={},
            )
            result: list[RAGEntry] = []
            for chunk in chunks:
                if hasattr(chunk, "page_content"):
                    content = chunk.page_content
                elif isinstance(chunk, dict):
                    content = chunk.get("content", chunk.get("text", str(chunk)))
                else:
                    content = str(chunk)
                if not content or not content.strip():
                    continue
                result.append(RAGEntry(content=content, metadata=metadata, file_id=file_metadata.get("id", "")))
            return result
        except Exception as e:
            logger.error(f"Chunk conversion failed: {e}")
            raise ProcessingError(f"Chunk conversion failed: {e}") from e

    def store_chunks(self, chunks: list[RAGEntry]) -> None:
        if not chunks:
            logger.warning("No chunks to store")
            return

        stored_count = 0
        failed_count = 0
        max_retries = 3

        for i, chunk in enumerate(chunks):
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    content_for_keywords = (
                        chunk.metadata.table_resume
                        if hasattr(chunk.metadata, "table_resume") and chunk.metadata.table_resume
                        else chunk.content
                    )
                    try:
                        chunk.metadata.keywords = self.keyword_generator.generate_keywords(content_for_keywords)
                    except Exception as e:
                        logger.warning(f"Keyword generation failed for chunk {i}: {e}")
                        chunk.metadata.keywords = []

                    vector = None
                    if hasattr(chunk.metadata, "vector") and chunk.metadata.vector:
                        vector = chunk.metadata.vector
                    else:
                        vector = self.embeddings.embed_query(chunk.content)

                    chunk.metadata.chunk_idx = f"{chunk.metadata.file_name}_{i}"

                    properties = chunk.model_dump(exclude={"metadata": {"header_pages", "vector"}})
                    self.collection.data.insert(properties=properties, vector=vector)
                    stored_count += 1
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(f"Failed to store chunk {i} after {max_retries} retries: {e}")
                        failed_count += 1
                        break
                    else:
                        logger.warning(f"Chunk storage failed (attempt {retry_count}/{max_retries}): {e}")
                        sleep(1.0 * retry_count)

        logger.info(f"Storage complete: {stored_count} stored, {failed_count} failed")
        if failed_count > 0:
            raise StorageError(f"Failed to store {failed_count}/{len(chunks)} chunks")
