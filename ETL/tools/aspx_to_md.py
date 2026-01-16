"""Converting file."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


class ImagePathProcessor:
    """Handles the extraction and reference updating of images without downloading."""

    def __init__(
        self,
        local_base_path: Path | None = None,
        *,
        verbose: bool = False,
    ) -> None:
        """Initialize the image path processor.

        Args:
            local_base_path (Path, optional): Base path for local image files
            verbose (bool, optional): Whether to print detailed logs

        """
        self.local_base_path = local_base_path or Path(
            r"C:\Source\parsing_tests\SitePages",
        )
        self.processed_images = {}  # Maps original URLs to new local paths
        self.failed_images = []  # List of URLs that couldn't be processed
        self.verbose = verbose

        # SharePoint paths to replace - will be replaced with local_base_path
        self.sharepoint_path_prefix = "/sites/EMS/SiteAssets/SitePages"

    def get_local_image_path(self, src: str) -> str:
        """Convert a SharePoint image URL to a local file path.

        Args:
            src (str): Image source URL

        Returns:
            str: Local file path or None if cannot be processed

        """
        if src in self.processed_images:
            return self.processed_images[src]

        if not src:
            return None

        # Skip data URLs
        if src.startswith("data:"):
            return src

        try:
            # Check if the URL starts with the SharePoint path prefix
            if src.startswith(self.sharepoint_path_prefix):
                # Extract the path after the SharePoint prefix
                relative_path = src[len(self.sharepoint_path_prefix) :].lstrip("/")

                # Create local path using the base path and relative path
                local_path = self.local_base_path / relative_path

                self.processed_images[src] = local_path
                return local_path

            self.failed_images.append(src)
            return src  # noqa: TRY300 Return original for now, may improve this fallback later
        except Exception:  # noqa: BLE001
            self.failed_images.append(src)
            return src

    def process_html_images(self, html_content: str) -> str:  # noqa: C901
        """Process all images in the HTML content and update references to local paths.

        Args:
            html_content (str): HTML content

        Returns:
            str: Updated HTML content with local image references

        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Process standard img tags
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src:
                continue

            # Get the local path
            local_path = self.get_local_image_path(src)

            if local_path:
                # Update the img tag with the new source
                img["src"] = local_path

        # 2. Process SharePoint imagePlugin divs
        for div in soup.find_all("div", {"class": "imagePlugin"}):
            # Extract image URL from data-imageurl attribute
            image_url = div.get("data-imageurl")

            if not image_url:
                continue

            # Get the local path
            local_path = self.get_local_image_path(image_url)

            if local_path:
                # Create a new img tag to replace the div
                new_img = soup.new_tag("img")
                new_img["src"] = local_path

                # Copy dimensions if available
                if div.get("data-height"):
                    new_img["height"] = div["data-height"]
                if div.get("data-width"):
                    new_img["width"] = div["data-width"]

                # Add alt text if available
                if div.get("data-imagetitle"):
                    new_img["alt"] = div["data-imagetitle"]

                # Replace the div with the new img tag
                div.replace_with(new_img)

        # 3. Process SharePoint-specific image data attributes
        for element in soup.find_all(attrs={"data-sp-prop-name": "imageSource"}):
            src = element.get("src")
            if not src:
                continue

            # Get the local path
            local_path = self.get_local_image_path(src)

            if local_path:
                # Update the element with the new source
                element["src"] = local_path

        return str(soup)


def extract_direct_image_urls(content: str) -> str:
    """Extract image URLs directly from the ASPX content before any processing.

    Args:
        content (str): ASPX file content

    Returns:
        list: List of extracted image URLs

    """
    image_urls = []

    # Extract URLs from standard img tags
    img_matches = re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', content)
    image_urls.extend(img_matches)

    # Extract URLs from imagePlugin divs
    plugin_matches = re.findall(r'data-imageurl="([^"]*)"', content)
    image_urls.extend(plugin_matches)

    # Extract URLs from SharePoint banner components
    banner_matches = re.findall(
        r'data-sp-prop-name="imageSource"[^>]*src="([^"]*)"',
        content,
    )
    image_urls.extend(banner_matches)

    # Extract URLs from data-imageSources in webpart data
    webpart_matches = re.findall(r'"imageSources"[^{]*{[^{]*"([^"]*)"[^}]*}', content)
    image_urls.extend(webpart_matches)

    return list(set(image_urls))  # Remove duplicates


def convert_aspx_to_markdown(
    input_file: Path,
    output_file: Path | None = None,
    local_base_path: Path | None = None,
    *,
    verbose: bool = False,
) -> str:
    """Convert a SharePoint ASPX file to Markdown.

    Args:
        input_file (Path): Path to the input ASPX file
        output_file (Path, optional): Path to the output Markdown file. If not provided,
                                    will use the input filename with .md extension
        local_base_path (Path, optional): Base path for local image files
        verbose (bool, optional): Whether to print detailed logs

    Returns:
        str: the converted content.

    """
    # Set default output filename if not provided
    if output_file is None:
        output_file = Path(input_file).with_suffix(".md")
    # Initialize image processor
    img_processor = ImagePathProcessor(
        local_base_path=local_base_path,
        verbose=verbose,
    )

    # Read input file
    with Path(input_file).open(encoding="utf-8") as file_:
        content = file_.read()

    # First convert ASPX to HTML
    html_content = convert_aspx_string_to_html(content)

    # Process images in HTML
    html_with_images = img_processor.process_html_images(html_content)

    # Then convert HTML to Markdown
    return md(html_with_images)


def convert_aspx_string_to_html(aspx_content: str) -> str:
    """Convert ASPX content provided as a string to HTML.

    Args:
        aspx_content (str): ASPX content as a string

    Returns:
        str: HTML content

    """
    # Extract the page title
    title_match = re.search(r"<title>(.*?)</title>", aspx_content)
    page_title = title_match.group(1) if title_match else "Converted Page"

    extracted_content = ""

    # Try multiple extraction methods in order of preference
    extraction_methods = [
        extract_from_canvas_content,
        extract_from_rte_divs,
        extract_from_webparts,
        extract_from_body,
    ]

    for method in extraction_methods:
        extracted = method(aspx_content)
        if extracted and len(extracted.strip()) > 0:
            extracted_content = extracted
            break

    # If nothing was extracted, use a placeholder
    if not extracted_content or len(extracted_content.strip()) == 0:
        extracted_content = "<p>No content could be extracted from the ASPX file.</p>"

    # Create a clean HTML structure
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{page_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
{extracted_content}
</body>
</html>
"""


def extract_from_canvas_content(content: str) -> str:
    """Extract content from SharePoint's CanvasContent1 section."""
    canvas_content_match = re.search(
        r"<mso:CanvasContent1[^>]*>(.*?)</mso:CanvasContent1>",
        content,
        re.DOTALL,
    )

    if not canvas_content_match:
        return None

    canvas_content = canvas_content_match.group(1)

    # Decode SharePoint specific HTML entities
    canvas_content = decode_sharepoint_entities(canvas_content)

    # Extract and convert SharePoint image plugins to standard HTML
    canvas_content = convert_sharepoint_image_plugins(canvas_content)

    # Try to clean up the content
    return clean_sharepoint_html(canvas_content)


def extract_from_rte_divs(content: str) -> str:
    """Extract content from data-sp-rte (Rich Text Editor) divs."""
    # Decode the content first
    decoded_content = decode_sharepoint_entities(content)

    # Find all Rich Text Editor divs
    rte_pattern = r'<div data-sp-rte="[^"]*">(.*?)</div>'
    rte_matches = re.findall(rte_pattern, decoded_content, re.DOTALL)

    if not rte_matches:
        return None

    extracted_content = ""
    for match in rte_matches:
        # Clean up nested attributes
        cleaned_match = clean_sharepoint_html(match)
        if cleaned_match.strip():
            extracted_content += cleaned_match + "\n"

    return extracted_content


def extract_from_webparts(content: str) -> str:
    """Extract content from SharePoint web parts."""
    decoded_content = decode_sharepoint_entities(content)

    # Look for content in webpart data
    webpart_pattern = r'data-sp-webpartdata="[^"]*"'
    if re.search(webpart_pattern, decoded_content):
        # Find searchable plain texts in webparts
        text_pattern = r"searchablePlainTexts&[^;]*;&[^;]*;([^&]*?)&"
        text_matches = re.findall(text_pattern, decoded_content, re.DOTALL)

        if text_matches:
            extracted_content = ""
            for match in text_matches:
                if match.strip() and not match.startswith("#"):
                    extracted_content += f"<p>{match}</p>\n"
            return extracted_content

    return None


def extract_from_body(content: str) -> str | None:
    """Extract content from the body section as a last resort."""
    body_match = re.search(r"<body[^>]*>(.*?)</body>", content, re.DOTALL)
    if body_match:
        body_content = body_match.group(1)
        # Try to clean up the content
        return clean_sharepoint_html(body_content)

    return None


def decode_sharepoint_entities(content: str) -> str:
    """Decode SharePoint specific HTML entities."""
    # Basic HTML entities
    decoded = content.replace("&amp;", "&")
    decoded = decoded.replace("&lt;", "<")
    decoded = decoded.replace("&gt;", ">")
    decoded = decoded.replace("&quot;", '"')

    # SharePoint specific encoding
    decoded = decoded.replace("&#58;", ":")
    decoded = decoded.replace("&#123;", "{")
    decoded = decoded.replace("&#125;", "}")
    decoded = decoded.replace("&#160;", "&nbsp;")
    decoded = decoded.replace("&amp;#58;", ":")
    decoded = decoded.replace("&amp;#123;", "{")
    decoded = decoded.replace("&amp;#125;", "}")
    decoded = decoded.replace("&amp;#160;", "&nbsp;")

    # Handle more complex number entities
    entities = re.findall(r"&#(\d+);", decoded)
    for entity in entities:
        try:
            char_code = int(entity)
            decoded = decoded.replace(f"&#{entity};", chr(char_code))
        except (ValueError, OverflowError):  # noqa: PERF203
            pass

    return decoded


def convert_sharepoint_image_plugins(content: str) -> str:
    """Convert SharePoint image plugins to standard HTML img tags.

    Args:
        content (str): HTML content containing SharePoint image plugins

    Returns:
        str: HTML content with image plugins converted to standard img tags

    """
    # Pattern to find SharePoint image plugins
    pattern = r'<div class="imagePlugin"[^>]*data-imageurl="([^"]*)"[^>]*>(.*?)</div>'

    def replace_plugin(match) -> str:  # noqa: ANN001
        image_url = match.group(1)

        # Extract additional attributes if available
        attributes = {}
        div_attrs = match.group(0)

        # Extract width and height
        width_match = re.search(r'data-width="([^"]*)"', div_attrs)
        height_match = re.search(r'data-height="([^"]*)"', div_attrs)

        if width_match:
            attributes["width"] = width_match.group(1)
        if height_match:
            attributes["height"] = height_match.group(1)

        # Extract alt text/title
        title_match = re.search(r'data-imagetitle="([^"]*)"', div_attrs)
        if title_match:
            attributes["alt"] = title_match.group(1)

        # Create an HTML img tag
        img_tag = f'<img src="{image_url}"'
        for attr, value in attributes.items():
            img_tag += f' {attr}="{value}"'
        img_tag += ">"

        return img_tag

    # Replace all image plugins with standard img tags
    return re.sub(pattern, replace_plugin, content)


def clean_sharepoint_html(content: str) -> str:
    """Clean up SharePoint specific HTML attributes and tags."""
    # Remove SharePoint specific data attributes, but preserve image data
    cleaned = re.sub(r' data-sp-(?!prop-name="imageSource")[^=]*="[^"]*"', "", content)

    # Convert imagePlugin divs to standard img tags if they weren't converted already
    image_plugin_pattern = (
        r'<div class="imagePlugin"[^>]*data-imageurl="([^"]*)"[^>]*>(.*?)</div>'
    )

    def replace_image_plugin(match) -> str:  # noqa: ANN001
        image_url = match.group(1)
        return f'<img src="{image_url}">'

    cleaned = re.sub(image_plugin_pattern, replace_image_plugin, cleaned)

    soup = BeautifulSoup(cleaned, "html.parser")

    # Process any remaining imagePlugin divs that regex didn't catch
    for div in soup.find_all("div", {"class": "imagePlugin"}):
        image_url = div.get("data-imageurl")
        if image_url:
            img = soup.new_tag("img")
            img["src"] = image_url
            div.replace_with(img)

    # Remove empty or unnecessary elements
    for element in soup.find_all(["div", "span"]):
        # Check if element is just a container with no useful content
        if not element.get_text(strip=True) and not element.find_all(
            ["img", "a", "table", "iframe"],
        ):
            element.extract()

    # Convert back to string
    return str(soup)
