"""Scan a SharePoint Online (SPO) site for files and folders."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import requests
from ETL.tools.exceptions import SPOError
from ETL.tools.fs_constants import NEW_METADATA_FILE
from ETL.tools.settings import etl_settings, spo_settings

logger = logging.getLogger(__name__)


class SharePointScanner:
    """Class to scan SharePoint Online for files and folders."""

    def __init__(self, output_file: Path) -> None:
        """Initialize the SharePointScanner with the access token and output file."""
        self.spo_token = spo_settings.get_spo_token()
        self.output_file = output_file
        self.files_data = []  # List to store file information

    def scan_spo(self, folder_path: str | None = None) -> None:
        """Scan SharePoint Online for files and folders."""
        headers = {"Authorization": f"Bearer {self.spo_token}"}

        # Get the SharePoint site ID
        site_id = spo_settings.site_id

        # Determine the folder path to scan
        folder_path = folder_path or spo_settings.main_folder_path
        folder_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{folder_path}:/children"
        msg = f"--- --- Scanning folder: {folder_path}"
        logger.info(msg)
        folder_response = requests.get(folder_url, headers=headers, timeout=30)

        if folder_response.status_code == 200:  # noqa: PLR2004
            folder_data = folder_response.json()

            folders2scan = []
            this_folder = folder_data.get("value", [])
            for item in this_folder:
                if "folder" in item:  # If it's a folder
                    if "UAT" in item["name"] and etl_settings.prod_env:
                        # no UAT / test folder in prod
                        continue
                    folders2scan.append(f"{folder_path}/{item['name']}")
                elif "file" in item:  # If it's a file
                    file_info = {
                        "id": item["id"],
                        "name": item["name"],
                        "etag": item["eTag"],
                        "web_url": item["webUrl"],
                    }
                    self.files_data.append(file_info)
            for subfolder_path in folders2scan:
                self.scan_spo(
                    folder_path=subfolder_path,
                )  # Recursive call for subfolders

        else:
            msg = f"""Error accessing folder:
            {folder_response.status_code} - {folder_response.text}"""
            raise SPOError(msg)

    def save_to_json(self) -> None:
        """Save the collected file metadata to a JSON file."""
        with self.output_file.open("w") as json_file:
            json.dump(self.files_data, json_file, indent=4)
        msg = f"File data saved to {self.output_file}"
        logging.info(msg)  # noqa: LOG015


def get_file_metadata_from_spo(*, use_filesystem: bool) -> None | dict:
    """Scan SPO and save file metadata to a JSON file."""
    scanner = SharePointScanner(
        output_file=NEW_METADATA_FILE,
    )

    logger.info("--- Scanning SPO...")
    scanner.scan_spo()
    if use_filesystem:
        scanner.save_to_json()
        return None
    return scanner.files_data


if __name__ == "__main__":
    get_file_metadata_from_spo(use_filesystem=True)
