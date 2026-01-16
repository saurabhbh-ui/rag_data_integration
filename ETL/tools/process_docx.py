"""Process docx documents."""

from __future__ import annotations

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from langchain_openai import AzureChatOpenAI
from PIL import Image

from ETL.tools.glob_vars import styles
from ETL.tools.interpret_image import resume_image
from ETL.document_processor.base.models import RAGEntry, RAGMetadata
from ETL.tools.settings import (
    azure_openai_completion_settings,
)

logger = logging.getLogger(__name__)

# Mapping for heading styles (case-insensitive)
HEADING_STYLE_MAP = {
    "title": 1,
    "contenttitle": 1,
    "heading1": 2,
    "heading2": 3,
    "heading3": 4,
    "heading4": 5,
    "heading5": 6,
    "heading6": 7,
    "heading7": 8,
    "heading8": 9,
    "heading9": 10,
}


ns = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "v": "urn:schemas-microsoft-com:vml",
}


def save_image(
    element: Any,  # noqa: ANN401
    image_counter: int,
    doc: Document,
    output_dir: Path,
    llm_multimodal: AzureChatOpenAI,
) -> str:
    """Extract and save an image from the DOCX element with enhanced detection."""
    # 1. First try standard methods with content type validation
    result = _try_standard_image_extraction(
        element,
        doc,
        image_counter,
        output_dir,
        llm_multimodal,
    )
    if result:
        return result

    # 2. If standard methods fail, look for alternate representations
    return _find_alternate_image(
        element,
        doc,
        image_counter,
        output_dir,
        llm_multimodal,
    )


def _try_standard_image_extraction(
    element: Any,  # noqa: ANN401
    doc: Document,
    image_counter: int,
    output_dir: Path,
    llm_multimodal: AzureChatOpenAI,
) -> str:
    """Attempt to extract an image from the DOCX element using standard methods.

    Checks for standard image representations (e.g., a:blip, w14:contentPart)
    and validates content type.
    Returns a string describing the image or an empty string if not found.
    """
    # Check for standard image (a:blip)
    blip = element.find(".//a:blip", namespaces=ns)
    if blip is not None:
        embed = blip.get(f"{{{ns['r']}}}embed")
        if embed:
            return _process_relationship(
                embed,
                doc,
                image_counter,
                output_dir,
                llm_multimodal,
            )

    # Check for content part (w14:contentPart)
    content_part = element.find(".//w14:contentPart", namespaces=ns)
    if content_part is not None:
        embed = content_part.get(f"{{{ns['r']}}}id")
        if embed:
            return _process_relationship(
                embed,
                doc,
                image_counter,
                output_dir,
                llm_multimodal,
            )

    return ""


def _process_relationship(
    embed_id: str,
    doc: Document,
    image_counter: int,
    output_dir: Path,
    llm_multimodal: AzureChatOpenAI,
) -> str:
    """Extract image data from a relationship and save it if valid.

    Validates the content type and saves the image if it is supported.
    Returns a string describing the image or an empty string if not found.
    """
    rel = doc.part.rels.get(embed_id)
    if rel and rel.target_part:
        # Skip non-image content types
        if rel.target_part.content_type.startswith("image/"):
            image_data = rel.target_part.blob
            return _save_image_data(
                image_data,
                image_counter,
                output_dir,
                llm_multimodal,
            )
        msg = f"Skipping non-image part (content type: {rel.target_part.content_type})"
        logger.debug(msg)
    return ""


def _find_alternate_image(
    element: Any,  # noqa: ANN401
    doc: Document,
    image_counter: int,
    output_dir: Path,
    llm_multimodal: AzureChatOpenAI,
) -> str:
    """Search for alternate image representations in the DOCX element.

    Looks for images in parent elements, VML representations,
    relationship attributes, and binary data.
    Returns a string describing the image or an empty string if not found.
    """
    # 1. Check for alternate image data in parent elements
    parent = element.getparent()
    while parent is not None:
        parent_result = _try_standard_image_extraction(
            parent,
            doc,
            image_counter,
            output_dir,
            llm_multimodal,
        )
        if parent_result:
            return parent_result
        parent = parent.getparent()

    # 2. Look for VML representation (older Word formats)
    vml_data = element.find(".//v:imagedata", namespaces=ns)
    if vml_data is not None:
        embed = vml_data.get(f"{{{ns['r']}}}id")
        if embed:
            return _process_relationship(
                embed,
                doc,
                image_counter,
                output_dir,
                llm_multimodal,
            )

    # 3. Search through all relationships in the element
    for el in element.iter():
        for attr_name, attr_value in el.attrib.items():
            if "embed" in attr_name or "id" in attr_name:
                result = _process_relationship(
                    attr_value,
                    doc,
                    image_counter,
                    output_dir,
                    llm_multimodal,
                )
                if result:
                    return result

    # 4. Last resort: look for binary image data patterns
    bin_data = element.find(".//w:binData", namespaces=ns)
    if bin_data is not None and bin_data.text:
        # Try decoding base64 data

        image_data = base64.b64decode(bin_data.text)
        return _save_image_data(
            image_data,
            image_counter,
            output_dir,
            llm_multimodal,
        )

    logger.warning("No valid image found in element after exhaustive search")

    return ""


def _process_table(table: Any) -> str:  # noqa: ANN401
    """Process a DOCX table element and convert it to Markdown format."""
    table_content = []
    for row in table.findall(
        ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr",
    ):
        row_data = []
        for cell in row.findall(
            ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc",
        ):
            cell_text = "".join(
                node.text
                for node in cell.findall(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t",
                )
                if node.text
            )
            row_data.append(cell_text.strip())
        table_content.append(row_data)

    # Format the table as Markdown
    if table_content:
        markdown_table = []
        headers = (
            table_content[0] if table_content else []
        )  # Use the first row as headers
        markdown_table.append("| " + " | ".join(headers) + " |")
        markdown_table.append(
            "| " + " | ".join(["---"] * len(headers)) + " |",
        )  # Markdown header separator
        for row in table_content[1:]:
            markdown_table.append("| " + " | ".join(row) + " |")  # noqa: PERF401

        return "\n".join(markdown_table)

    logger.warning("Table is empty or not formatted correctly.")
    return ""


def _save_image_data(
    image_data: bytes,
    image_counter: int,
    output_dir: Path,
    llm_multimodal: AzureChatOpenAI,
    *,
    is_example: bool = True,
) -> str:
    """Save image data to disk and return a description.

    Detects image format, saves the image, and returns a description using resume_image.
    Returns an empty string if the image cannot be processed.
    """
    image = Image.open(BytesIO(image_data))

    # Handle cases where format couldn't be detected
    if not image.format:
        # Try to detect PNG by magic number
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            image_format = "png"
        # Try to detect JPEG
        elif image_data.startswith(b"\xff\xd8\xff"):
            image_format = "jpeg"
        else:
            logger.warning("Image format not recognized. Skipping.")
            return ""
    else:
        image_format = image.format.lower()

    if image_format in ("wmf", "emf"):
        return "IMAGE NOT RECOGNIZED."

    image_filename = f"image_{image_counter}.{image_format}"
    image_path = output_dir / image_filename
    image.save(image_path)
    return resume_image(
        image_path,
        llm_multimodal=llm_multimodal,
        is_example=is_example,
    )


def process_element(  # noqa: C901, PLR0912
    element: Any,  # noqa: ANN401
    image_counter: int,
    doc: Document,
    output_dir: Path,
    llm_multimodal: AzureChatOpenAI,
) -> str:
    """Recursively process a DOCX XML element.

    Handles paragraphs, tables, structured document tags, and container elements.
    Extracts text, images, and tables, formatting them as Markdown.
    Returns a list of extracted content strings.
    """
    results = []
    tag = element.tag

    # Handle paragraphs (text, headings, and images)
    if tag.endswith("p"):
        # Check if this is a heading
        heading_level = None
        p_p_r = element.find("w:pPr", namespaces=ns)

        if p_p_r is not None:
            # Check outline level first
            outline_elem = p_p_r.find("w:outlineLvl", namespaces=ns)
            if outline_elem is not None:
                try:
                    outline_level = int(outline_elem.get(f"{{{ns['w']}}}val", "0"))
                    heading_level = min(
                        outline_level + 1,
                        6,
                    )  # Convert to Markdown level (max h6)
                except ValueError:
                    pass
            # Check paragraph style if outline level not found
            if heading_level is None:
                style_elem = p_p_r.find("w:pStyle", namespaces=ns)
                if style_elem is not None:
                    style_name = style_elem.get(f"{{{ns['w']}}}val", "").lower()
                    styles.add(style_name)
                    heading_level = HEADING_STYLE_MAP.get(style_name)

        paragraph_text = []
        for run in element.iterchildren():
            if run.tag.endswith("r"):  # Text run
                text = "".join(t.text for t in run.iterchildren() if t.text)
                drawing = run.find(".//w:drawing", namespaces=ns)
                if drawing is not None:
                    image_resume = save_image(
                        drawing,
                        image_counter[0],
                        doc=doc,
                        output_dir=output_dir,
                        llm_multimodal=llm_multimodal,
                    )
                    paragraph_text.append(image_resume)
                    image_counter[0] += 1
                elif text:
                    hyperlink = run.find(".//w:hyperlink", namespaces=ns)
                    if hyperlink is not None:
                        # Preserve hyperlink text
                        hl_text = "".join(
                            t.text for t in hyperlink.iterchildren() if t.text
                        )
                        paragraph_text.append(hl_text)
                    else:
                        paragraph_text.append(text)

        full_text = "".join(paragraph_text).strip()
        if full_text:
            if heading_level is not None:
                # Format as Markdown heading
                results.append(f"{'#' * heading_level} {full_text}")
            else:
                results.append(full_text)

    # Process tables
    elif tag.endswith("tbl"):
        results.append(_process_table(table=element))

    # Process SDT (Structured Document Tags)
    elif tag.endswith("sdt"):
        sdt_content = element.find(".//w:sdtContent", namespaces=ns)
        if sdt_content is not None:
            for child in sdt_content.iterchildren():
                results.extend(
                    process_element(
                        child,
                        image_counter,
                        doc=doc,
                        output_dir=output_dir,
                        llm_multimodal=llm_multimodal,
                    ),
                )

    # Recursively process other container elements
    else:
        for child in element.iterchildren():
            results.extend(
                process_element(
                    child,
                    image_counter,
                    doc=doc,
                    output_dir=output_dir,
                    llm_multimodal=llm_multimodal,
                ),
            )

    return results


def extract_docx_elements(
    doc: Document,
    llm_multimodal: AzureChatOpenAI,
    output_dir: Path = Path("images"),
) -> list[str]:
    """Extract text, tables, and images from a DOCX document.

    Returns a list where:
        - Text is preserved with formatting (including hyperlinks)
        - Headings are converted to Markdown headers (#, ##, etc.)
        - Tables are represented as markdown
        - Images are saved and replaced with descriptive text
    Handles nested structures like SDT (Structured Document Tags).

    """
    # Ensure the output directory for images exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Start processing from the document body
    body = doc.element.body
    output = []
    image_counter = [1]  # Use a list to allow modification within nested functions
    for child in body.iterchildren():
        output.extend(
            process_element(
                child,
                image_counter,
                doc=doc,
                output_dir=output_dir,
                llm_multimodal=llm_multimodal,
            ),
        )

    return output


def extract_text_images_and_tables(
    doc: Document,
    output_txt_file: str,
    llm_multimodal: AzureChatOpenAI,
) -> str:
    """Extract data from document."""
    paragraphs = extract_docx_elements(doc=doc, llm_multimodal=llm_multimodal)

    full_doc_text = "\n\n".join(paragraphs)
    if output_txt_file is not None:
        # Save the extracted content to a .txt file
        with output_txt_file.open(mode="w", encoding="utf-8") as txt_file:
            txt_file.write(full_doc_text)
    return full_doc_text


def process_docx(
    docx_file: Path,
    file_metadata: dict,
    llm_multimodal: AzureChatOpenAI,
) -> RAGEntry:
    """Extract text, images, and tables."""
    doc = Document(docx_file)

    # Define the output .txt file name based on the input .docx file name
    output_txt_file = docx_file.with_suffix(".txt")

    # Extract text, images, and tables
    full_doc_text = extract_text_images_and_tables(
        doc,
        output_txt_file=output_txt_file,
        llm_multimodal=llm_multimodal,
    )

    metadata = RAGMetadata(
        source=file_metadata["web_url"],
        file_name=docx_file.name,
        file_type=docx_file.suffix,
        etag=file_metadata["etag"],
        document_title=docx_file.stem,
    )

    return RAGEntry(
        content=full_doc_text,
        metadata=metadata,
        file_id=file_metadata["id"],
    )


if __name__ == "__main__":
    docx_file_path = Path(
        "ETL/data/Guidance on accommodation services for event participants.docx",
    )

    if docx_file_path.exists():
        llm = AzureChatOpenAI(
            azure_endpoint=azure_openai_completion_settings.endpoint,
            azure_deployment=azure_openai_completion_settings.deployment,
            api_key=azure_openai_completion_settings.api_key,
            api_version=azure_openai_completion_settings.api_version,
            temperature=0.0,  # Keep temperature low for focused keywords
            verbose=True,
            streaming=False,
        )
        file_metadata = {
            "file_path": docx_file_path,
            "etag": "asd",
            "id": "asd",
            "web_url": "https://asdasdasd",
        }
        process_docx(docx_file_path, file_metadata=file_metadata, llm_multimodal=llm)
    else:
        msg = f"File not found: {docx_file_path}"
        logger.info(msg)
