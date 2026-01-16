"""Functions to resume the content of a table/ Pandas dataframe."""

import logging
import time

import pandas as pd
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from ETL.tools.exceptions import MaxRetriesError
from ETL.tools.settings import etl_settings


def generate_document_resume(
    filename: str,
    content: str,
    llm_model: AzureChatOpenAI,
) -> str:
    """Generate a resume of a document."""
    messages = [
        (
            "system",
            """You are a specialized document resume writer that works for the
            BIS, the Bank for Internationasl Settlements.
            Your role is to create
            short semantic descriptions of documents.
            Your descriptions should be detailed enough to enable
            semantic search and matching against user queries,
            but really short, like ten to twenty words.""",
        ),
        (
            "human",
            f"""Resume this document that comes from the file named '{filename}':

        {content}""",
        ),
    ]
    retries = 0
    while retries < etl_settings.api_calls_max_retries:
        try:
            response = llm_model.invoke(messages)

        except Exception as e:  # noqa: PERF203
            retries += 1
            if retries < etl_settings.api_calls_max_retries:
                msg = f"""RateLimitError encountered.
                Retrying in {etl_settings.api_calls_retries_delay}
                seconds... (Attempt {retries}/{3})"""
                logging.warning(msg)  # noqa: LOG015
                time.sleep(etl_settings.api_calls_retries_delay)
            else:
                msg = "Max retries reached. Unable to process the request."
                raise MaxRetriesError(msg) from e
        else:
            return response.content
    return ""


def generate_table_resume(
    filename: str,
    sheet_name: str,
    sheet_data: pd.DataFrame,
    llm_model: AzureChatOpenAI,
    embeddings_model: AzureOpenAIEmbeddings,
) -> tuple[list, str]:
    """Generate a vector corresponding to the resume of a table."""
    messages = [
        (
            "system",
            """You are a specialized table analyzer that works for the
            BIS, the Bank for Internationasl Settlements.
            Your role is to create
            short semantic descriptions of tabular data.
            Your descriptions should be detailed enough to enable
            semantic search and matching against user queries.
            Focus on identifying the table's purpose, main entities,
            key metrics, time periods, and relationships between data elements.""",
        ),
        (
            "human",
            f"""Analyze this table from the Excel file '{filename}',
            sheet named '{sheet_name}':

        {sheet_data.to_markdown()}

        Create a short description that covers the main subject and purpose
        of this table.

        Be specific and use terminology that would match how a user
        might search for this information.
        """,
        ),
    ]
    retries = 0
    while retries < etl_settings.api_calls_max_retries:
        try:
            response = llm_model.invoke(messages)
            resume = response.content
            return embeddings_model.embed_query(resume), resume

        except Exception as e:  # noqa: PERF203
            retries += 1
            if retries < etl_settings.api_calls_max_retries:
                msg = f"""RateLimitError encountered.
                Retrying in {etl_settings.api_calls_retries_delay}
                seconds... (Attempt {retries}/{3})"""
                logging.warning(msg)  # noqa: LOG015
                time.sleep(etl_settings.api_calls_retries_delay)
            else:
                msg = "Max retries reached. Unable to process the request."
                raise MaxRetriesError(msg) from e
    return [], ""
