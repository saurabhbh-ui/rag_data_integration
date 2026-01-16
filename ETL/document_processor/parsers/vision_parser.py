
from __future__ import annotations
from pathlib import Path
from typing import Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from langchain_openai import AzureChatOpenAI

from ETL.document_processor.parsers.base_parser import BaseParser
from ETL.document_processor.base.interfaces import Parser
from ETL.document_processor.base.models import ProcessingConfig
from ETL.tools.doc_etl_components import etl_components  # type: ignore
from ETL.tools.parser import parse_pdf_file_with_document_intelligence  # type: ignore

import logging

logger = logging.getLogger(__name__)


class VisionParser(BaseParser, Parser):
    """Vision-based parser for PDFs, producing stitched or sequential markdown."""
    def __init__(self, llm: AzureChatOpenAI, di_client: Optional[DocumentIntelligenceClient] = None, config: ProcessingConfig | None = None):
        super().__init__(config)
        self.llm = llm
        self.di_client = di_client

    def supports_file_type(self, file_extension: str) -> bool:
        return file_extension.lower() in [".pdf"]

    def parse(self, file_path: Path, file_metadata: dict, **kwargs) -> tuple[str, int]:
        image_processor = etl_components(file=file_path.as_posix(), llm_multimodal=self.llm)

        image_map = image_processor.pdf_to_base64_utf8_images(blob_pdf_path=file_path.as_posix())
        images = list(image_map.values())
        if not images:
            logger.warning(f"No images extracted from {file_path.name}")
            return "", 0

        page_summaries = []
        for i, img in enumerate(images, 1):
            try:
                print(f"Processing image {i}/{len(images)}")
                summary = image_processor.new_summarize_image(img)
                page_summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to summarize image page {i}: {e}")
                page_summaries.append("")

        if self.config.document_page_stitching and self.di_client:
            try:
                di_result = parse_pdf_file_with_document_intelligence(
                    bytes_source=file_path.with_suffix(".pdf").read_bytes(),
                    client=self.di_client
                )
                reference_text = di_result["result"].content if di_result and "result" in di_result else ""
                stitched = image_processor.stitch_pages(reference_text=reference_text, page_contents_list=page_summaries)
                return stitched, 0
            except Exception as e:
                logger.warning(f"Stitching failed, falling back to simple concatenation: {e}")

        concatenated = ""
        for i, page in enumerate(page_summaries, 1):
            concatenated += f"\n{'='*80}\nPAGE {i}\n{'='*80}\n{page}\n{'='*80}\n"

        return concatenated, 0