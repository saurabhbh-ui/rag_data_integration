from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
import requests
from docx2pdf import convert
from ETL.tools.fs_constants import DOWNLOAD_DIR
from ETL.document_processor.utils.settings import spo_settings, etl_settings


logger = logging.getLogger(__name__)

def download_file(file: dict, convert_to_pdf: bool = False) -> Path:
    """Download a file from SPO and save it to the local directory."""
    if convert_to_pdf and ("docx" in file["name"]):
        print("Converting DOCX to PDF...")
        file_path = Path(DOWNLOAD_DIR / file["name"].replace(".docx", ".pdf"))
        download_url = f"https://graph.microsoft.com/v1.0/sites/{spo_settings.site_id}/drive/items/{file['id']}/content?format=pdf"
    else:
        print("Docx remain Docx")
        file_path = Path(DOWNLOAD_DIR / file["name"])
        download_url = f"https://graph.microsoft.com/v1.0/sites/{spo_settings.site_id}/drive/items/{file['id']}/content"
        
    # Set the headers
    access_token = spo_settings.get_spo_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    # Send the GET request
    response = requests.get(download_url, headers=headers, timeout=30)

    # Save the file if the request is successful

    if response.status_code == 200:  # noqa: PLR2004
        with file_path.open("wb") as f:
            f.write(response.content)
        msg = f"File {file_path.stem} downloaded successfully!"
    else:
        msg = f"""Failed to download file {file_path.stem}:
            {response.status_code}, {response.text}"""
    logger.info(msg)

    return file_path


def convert_to_pdf(input_file):
    """
    Convert a file to PDF based on its extension.

    Args:
        input_file (str): Path to the input file

    Returns:
        str: Path to the output PDF file if successful, False otherwise
    """

    # Check if file exists
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        return False

    # Get file extension and output path
    file_ext = Path(input_file).suffix.lower()
    output_file = Path(input_file).with_suffix('.pdf')

    # Skip if already a PDF (case-insensitive)
    if file_ext == '.pdf':
        print(f"File '{input_file}' is already a PDF. Skipping conversion and not deleting the file.")
        return Path(input_file)

    try:
        if file_ext == '.docx':
            # DOCX to PDF
            convert(input_file, output_file)

        else:
            print(f"Unsupported file type: {file_ext}")
            return False

        # Remove the original file (only if it was converted)
        os.remove(input_file)
        print(f"Successfully converted {input_file} to {output_file} and removed the original file.")
        return Path(output_file)

    except ImportError as e:
        print(f"Required library not found: {e}")
        print("Please install: pip install docx2pdf comtypes fpdf")
        return False
    except Exception as e:
        print(f"Conversion failed for {input_file}: {e}")
        return False
