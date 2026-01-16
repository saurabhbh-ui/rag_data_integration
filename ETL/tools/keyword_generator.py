"""Generate keywords."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field, field_validator

from ETL.tools.exceptions import MaxRetriesError

logger = logging.getLogger(__name__)


def invoke_with_retry(  # noqa: RET503
    llm: AzureChatOpenAI,
    messages: list[dict],
    schema: type[BaseModel],
    max_retries: int = 5,
    backoff_factor: int = 2,
) -> dict:
    """Invoke the LLM with retry logic for rate limit errors.

    Args:
        llm: The LLM instance.
        messages: The input messages for the LLM.
        schema: Pydantic schema for structured output.
        max_retries: Maximum number of retries.
        backoff_factor: Factor by which the wait time increases after each retry.

    Returns:
        The response from the LLM.

    Raises:
        MaxRetriesError: If the maximum number of retries is exceeded.

    """
    retries = 0
    wait_time = 4  # Initial wait time in seconds

    while retries <= max_retries:
        try:
            # Get structured output using Pydantic model
            structured_llm = llm.with_structured_output(
                schema=schema,
                method="json_mode",
            )
            return structured_llm.invoke(messages)
        except Exception as e:  # noqa: PERF203
            if (
                "rate limit" in str(e).lower() or "ratelimit" in str(e).lower()
            ):  # Check if it's a rate limit error
                retries += 1
                if retries > max_retries:
                    msg = f"Rate limit exceeded after {max_retries} retries."
                    raise MaxRetriesError(msg) from e
                msg = f"Rate limit error. Retrying in {wait_time} seconds..."
                logger.info(msg)
                time.sleep(wait_time)
                wait_time *= backoff_factor  # Exponential backoff
            else:
                raise  # Re-raise other exceptions that aren't rate limit errors


class KeywordResponse(BaseModel):
    """Response model."""

    keywords: list[str] = Field(
        min_length=4,
        max_length=6,
        description="List of 4-6 general keywords extracted from the text",
    )

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, keywords: list[str]) -> list[str]:
        """Verify the keywords are the ones expected."""
        # Validate number of keywords
        if not (4 <= len(keywords) <= 6):  # noqa: PLR2004
            msg = f"Must provide between 4 and 6 keywords, got {len(keywords)}"
            raise ValueError(msg)

        # Validate individual keywords
        for keyword in keywords:
            if len(keyword) > 40:  # noqa: PLR2004
                msg = f"Keyword '{keyword}' exceeds maximum length of 40 characters"
                raise ValueError(msg)
            if not keyword.strip():
                msg = "Empty keywords are not allowed"
                raise ValueError(msg)
        return keywords


class KeywordGenerator:
    """Use LLM to generate keywords."""

    def __init__(self, llm: AzureChatOpenAI) -> None:
        """Init the class."""
        self.llm = llm
        self.prompt_template = """
        You are an expert in identifying keywords in text.

        TEXT: {text}

        Generate exactly 4-6 keywords for the TEXT above.
        The keywords should be general in nature
        and not mention specific names.

        Provide your response in the following JSON format:
        {{
            "keywords": ["keyword1", "keyword2", "keyword3", "keyword4"]
        }}

        Requirements:
        - Return exactly 4-6 keywords
        - Each keyword must be under 40 characters
        - Keywords must be general concepts (no proper nouns or specific names)
        - Format must be a valid JSON object with a "keywords" array
        - Keywords must not be empty or only whitespace
        """

    def generate_keywords(self, text: str) -> list[str]:
        """Generate keywords for the given text."""
        prompt = self.prompt_template.format(text=text)

        # Create message for the LLM
        messages = [
            {
                "role": "system",
                "content": """You are a keyword extraction expert.
                Always respond with exactly 4-6 keywords in
                the specified JSON format.""",
            },
            {"role": "user", "content": prompt},
        ]

        # Get structured output using Pydantic model
        response = invoke_with_retry(
            llm=self.llm,
            messages=messages,
            schema=KeywordResponse,
        )

        # Validate the response using Pydantic
        structured_response = KeywordResponse.model_validate(response)

        return structured_response.keywords
