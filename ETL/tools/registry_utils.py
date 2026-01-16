# C:\Users\sa007769\Downloads\rag_etl\bis-gpt-rag-etl\ETL\tools\registry_utils.py
"""Utilities for fetching ETL configurations from App Registry API."""

import logging
import requests
from typing import List
from pydantic import BaseModel
from ETL.tools.settings import registry_settings

logger = logging.getLogger(__name__)

class ETLSource(BaseModel):
    """Configuration for an ETL process from App Registry."""
    
    clientId: str
    root: str
    mainFolder: str
    applicationId: int
    applicationName: str | None = None
    chunkerType: str
    parserType: str
    chunkAugmentationMethod: str

def get_etl_sources() -> List[ETLSource]:
    """
    Fetch ETL configurations from the App Registry API.
    
    Returns:
        List of ETLSource objects containing ETL configurations
        
    Raises:
        requests.exceptions.RequestException: If the API call fails
        ValueError: If the response cannot be parsed
    """
    logger.info(f"Fetching ETL configurations from registry: {registry_settings.list_etl_url}")
    
    try:
        response = requests.get(registry_settings.list_etl_url, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        
        etl_sources = [ETLSource(**item) for item in json_data]
        logger.info(f"Successfully fetched {len(etl_sources)} ETL configurations")
        
        return etl_sources
        
    except requests.exceptions.RequestException as e:
        msg = f"Failed to fetch ETL configurations from registry: {e}"
        logger.exception(msg)
        raise  # Re-raise the exception instead of sys.exit
    except Exception as e:
        msg = f"Error parsing ETL configurations: {e}"
        logger.exception(msg)
        raise ValueError(msg) from e  # Raise ValueError instead of sys.exit
