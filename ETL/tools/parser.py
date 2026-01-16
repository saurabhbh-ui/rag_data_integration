"""Functions to parse PDFs."""

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult, AnalyzeOutputOption

from ETL.document_processor.base.models import RAGEntry, RAGMetadata


def parse_pdf_file_with_document_intelligence(
    client: DocumentIntelligenceClient,
    bytes_source: bytes,
) -> AnalyzeResult:
    """As the title."""
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(bytes_source=bytes_source),
        output_content_format="markdown", 
        output=[AnalyzeOutputOption.FIGURES]
    )
    result: AnalyzeResult = poller.result()

    figures = result.figures or []
    total_graphics_count = len(figures)

    print(f"Total graphic elements (figures) found: {total_graphics_count}")

    # Optional: inspect each graphic element
    images_coordinates = []
    for idx, fig in enumerate(figures, start=1):
        # boundingRegions tells you where on the page the graphic is
        locs = []
        if fig.bounding_regions:
            for br in fig.bounding_regions:
                locs.append(
                    f"page {br.page_number}, polygon={br.polygon}"
                )
        #print(f"- Figure #{idx}: id={fig.id}, locations={'; '.join(locs) or 'N/A'}")
        images_coordinates.extend(locs)

    return {'result':result, 'total_graphics_count': total_graphics_count, 'images_coordinates': images_coordinates}


def create_header_page_mapping(paragraphs: list) -> dict:
    """Create a mapping of header content to page numbers for section headings."""
    header_pages = {}

    for para in paragraphs:
        if para.get("role") in ["sectionHeading", "title"]:
            content = para["content"]
            # Get page number from the first bounding region
            if para.get("boundingRegions"):
                page_num = para["boundingRegions"][0]["pageNumber"]
                header_pages[content] = page_num

    return header_pages


def parse_pdf_docs(
    di_client: DocumentIntelligenceClient,
    file_metadata: dict,
) -> tuple[RAGEntry, int]:
    """Extract info from PDF files."""
    file_path = file_metadata["file_path"]

    pdf_path = file_path.with_suffix(".pdf")

    result = parse_pdf_file_with_document_intelligence(
        bytes_source=pdf_path.read_bytes(),
        client=di_client,
    )
    
    header_pages = create_header_page_mapping(result['result'].paragraphs)

    metadata = RAGMetadata(
        source=file_metadata["web_url"],
        file_name=file_path.name,
        file_type=file_path.suffix,
        etag=file_metadata["etag"],
        document_title=file_path.stem,
        header_pages=header_pages,
    )

    msdb_entry = RAGEntry(
        content=result["result"].content,
        metadata=metadata,
        file_id=file_metadata["id"],
    )
    
    return msdb_entry, result.get("total_graphics_count", 0)



def parse_text_or_markdown(file_path, file_metadata: dict) -> RAGEntry:
    """
    Parse text or markdown files and return an RAGEntry object.

    Args:
        file_path (Path): The path to the text or markdown file.
        file_metadata (dict): Metadata about the file (e.g., web_url, etag, etc.).

    Returns:
        RAGEntry: An object containing the file content and metadata.
    """
    try:
        # Read the content of the text/markdown file
        print(f"{type(file_path)}")
        file_name = file_path.as_posix()
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to read file {file_path}: {e}")

    # Create metadata for the file
    metadata = RAGMetadata(
        source=file_metadata.get("web_url", ""),
        file_name=file_path.name,
        file_type=file_path.suffix,
        etag=file_metadata.get("etag", ""),
        document_title=file_path.stem,
        header_pages={},  # Optional: Populate if you wish to extract headers/pages
    )

    # Create and return the RAGEntry object
    return RAGEntry(
        content=content,
        metadata=metadata,
        file_id=file_metadata.get("id", ""),
    )