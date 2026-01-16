"""Settings for the services used in the application."""

from __future__ import annotations

from functools import cached_property
from typing import Literal

import msal
import requests
from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, String, create_engine
from sqlalchemy.dialects import mssql
from sqlalchemy.exc import OperationalError

from ETL.tools.exceptions import DBError, SPOError

# Explicitly load the environment variables from the .env file
load_dotenv()


class RagAppSettings(BaseSettings):
    """Config settings for LLM."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="rag_",
        extra="ignore",
    )

    app_id: int


class RegistrySettings(BaseSettings):
    """Settings for Microsoft SQL Server authentication."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="app_registry_",
        extra="ignore",
    )

    address: str = Field(description="The address of the app registry")
    token_secret: str = Field(
        description="""The secret key for JWT token generation.
            The same must be defined in the AppRegistry.""",
    )
    port: int | None = Field(
        default=None,
        description="The port number for the app registry",
    )
    list_etl_endpoint: str = Field(
        default="/api/listETLConfigurations",
        description="The endpoint for listing ETL configurations",
    )

    @property
    def list_etl_url(self) -> str:
        """Return the scope."""
        if self.port is not None:
            return f"http://{self.address}:{self.port}{self.list_etl_endpoint}"
        return f"http://{self.address}{self.list_etl_endpoint}"


class ETLSettings(BaseSettings):
    """Config settings for LLM."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="etl_",
        extra="ignore",
    )

    prod_env: bool = Field(
        description="""if True, any file in a folder named UAT will be ignored.""",
    )
    download_as_pdf: bool = Field(
        description="If True, the docx files will be downloaded as PDF.",
    )
    chunk_augmentation_strategy: Literal["resume_on_top", "iterative", "none"] = Field(
        default="None",
        description="""Wheter augment chunks or not.

        Available strategies:

        - resume_on_top: add a short resume of the whole document to the begin
          of the chunk before embedding the same..
        - iterative: checks for potential issue with the chunk, then adds
          elements from the original documents to mitigate the same.

        """,
    )

    api_calls_max_retries: int = Field(
        description="""How many times to retry the call to LLM or embedding API
in case of failure.""",
        default=3,
    )
    api_calls_retries_delay: int = Field(
        description="Delay in seconds between retries.",
        default=5,
    )


class WeaviateSettings(BaseSettings):
    """Config settings for LLM."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="weaviate_",
        extra="ignore",
    )

    url: str
    collection_name: str


class SharePointOnlineSettings(BaseSettings):
    """Configuration settings for SharePoint Online integration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="spo_",
        extra="ignore",
    )

    client_id: str
    root: str
    secret: str
    main_folder_path: str
    tenant_id: str = "03e82858-fc14-4f12-b078-aac6d25c87da"
    main_spo: str = "bisadaz.sharepoint.com"
    scopes: list[str] = ["https://graph.microsoft.com/.default"]

    @computed_field
    @cached_property
    def site_id(self) -> float:
        """Returns the SharePoint Online site ID."""
        return self.get_site_id()

    def get_spo_token(self) -> str:
        """Get the auth token for SharePointOnline.

        Returns:
            str: The access token for SharePoint Online.

        Raises:
            SPOError: If unable to retrieve the access token.

        """
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            authority=authority,
            client_credential=self.secret,
        )
        token_response = app.acquire_token_for_client(scopes=self.scopes)
        if "access_token" in token_response:
            return token_response["access_token"]
        msg = f"unable to get access token:\n{token_response}"
        raise SPOError(msg)

    def get_site_id(self) -> str:
        """Retrieve the SharePoint Online site ID using Microsoft Graph API.

        Returns:
            str: The site ID.

        Raises:
            SPOError: If unable to retrieve the site ID.

        """
        spo_token = self.get_spo_token()
        headers = {"Authorization": f"Bearer {spo_token}"}

        site_url = f"https://graph.microsoft.com/v1.0/sites/{self.main_spo}:{self.root}"

        site_response = requests.get(site_url, headers=headers, timeout=30)

        if site_response.status_code == 200:  # noqa: PLR2004
            site_data = site_response.json()
            return site_data["id"]
        msg = f"""Error accessing site:
            {site_response.status_code} - {site_response.text}"""
        raise SPOError(msg)


class AzureOpenAICompletionSettings(BaseSettings):
    """Config settings for LLM."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="azure_oai_",
        extra="ignore",
    )

    endpoint: str
    deployment: str
    api_version: str
    api_key: str
    temperature: float = 0.0


class AzureOpenAIEmbeddingSettings(BaseSettings):
    """Config settings for Embedding model."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="azure_oai_emb_",
        extra="ignore",
    )

    endpoint: str
    deployment: str
    api_version: str
    api_key: str


class DocumentIntelligenceSettings(BaseSettings):
    """Config settings for DI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="di_",
        extra="ignore",
    )

    endpoint: str
    api_key: str


class SQLServerSettings(BaseSettings):
    """Settings for Microsoft SQL Server authentication."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="mssql_",
        extra="ignore",
    )

    server: str
    db_name: str
    driver: str = "ODBC+Driver+18+for+SQL+Server"
    trust_cert: bool = True

    @property
    def connection_string(self) -> str:
        """Return the scope."""
        trust_cert_str = "&TrustServerCertificate=yes" if self.trust_cert else ""
        #return f"mssql+pyodbc://{self.server}/{self.db_name}?driver={self.driver}{trust_cert_str}"
        connection_string = (
        f"mssql+pyodbc://{self.server}/{self.db_name}"
        f"?driver=ODBC+Driver+18+for+SQL+Server"
        f"{trust_cert_str}"
        )
        #print(f"Connection string: {connection_string}")
        return connection_string

    @property
    def engine(self) -> Engine:
        """Init sqlserver engine."""
        try:
            # Register the 'sysname' type with SQLAlchemy
            mssql.dialect.ischema_names["sysname"] = String
            return create_engine(self.connection_string)
        except OperationalError as e:
            raise DBError from e


etl_settings = ETLSettings()
weaviate_settings = WeaviateSettings()
spo_settings = SharePointOnlineSettings()
azure_openai_completion_settings = AzureOpenAICompletionSettings()
azure_openai_embedding_settings = AzureOpenAIEmbeddingSettings()
document_intelligence_settings = DocumentIntelligenceSettings()
sql_server_settings = SQLServerSettings()
rag_app_settings = RagAppSettings()
registry_settings = RegistrySettings()

