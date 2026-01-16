"""Inbterpret image(s) using multimodal LLM."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_openai import AzureChatOpenAI


import base64
import logging
import time
from pathlib import Path

from langchain.schema.messages import HumanMessage, SystemMessage

from ETL.tools.exceptions import InterpretationError, MaxRetriesError

logger = logging.getLogger(__name__)


def read_n_convert_image(image_path: str) -> str:
    """Read the image."""
    with Path(image_path).open("rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def throttle_summarize_image(
    encoded_image: str,
    llm_multimodal: AzureChatOpenAI,
    max_retries: int = 5,
    backoff_factor: int = 2,
    *,
    is_example: bool = False,
) -> str:
    """Summarize the content of the provided image using an LLM."""
    if is_example:
        h_m = """Describe this screenshot with one single paragraph.
                The information shown (dates, etc.) are actually examples,
                so state this in the answer in an appropriate way.
                """
    else:
        h_m = """Describe this screenshot with one single paragraph."""

    prompt = [
        SystemMessage(
            content="""You are a bot that is good at analyzing images, specifically
            screenshots of operations to be performed from the users in order to
            fulfill operations related to BIS (Bank for International Settlements)
            Meeting Services office, like: booking rooms, organizing events, etc.
            """,
        ),
        HumanMessage(
            content=[
                {"type": "text", "text": h_m},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
                },
            ],
        ),
    ]
    wait_time = 1  # Initial wait time in seconds

    retries = 0
    while retries < max_retries:
        try:
            response = llm_multimodal.invoke(prompt)
            return response.content  # noqa: TRY300
        except Exception as e:  # noqa: PERF203
            if (
                "rate limit" in str(e).lower() or "ratelimit" in str(e).lower()
            ):  # Check if it's a rate limit error
                retries += 1
                if retries > max_retries:
                    msg = f"Rate limit exceeded after {max_retries} retries."
                    raise MaxRetriesError(msg) from e
                msg = f"Rate limit reached. Retrying in {wait_time} seconds..."
                logger.info(msg)
                time.sleep(wait_time)
                wait_time *= backoff_factor  # Exponential backoff
            else:
                raise  # Re-raise other exceptions that aren't rate limit errors

    msg = "Max retries reached due to rate limit errors."
    raise MaxRetriesError(msg)


def process_images(
    inputs_images: list,
    llm_multimodal: AzureChatOpenAI,
    *,
    is_example: bool = True,
) -> list[str]:
    """Summarizes a list of images using the provided image processor."""
    summarize_images_list = []

    batch_summarize_images_list = [
        throttle_summarize_image(
            img,
            llm_multimodal=llm_multimodal,
            is_example=is_example,
        )
        for img in inputs_images
    ]
    summarize_images_list.extend(batch_summarize_images_list)

    return summarize_images_list


def resume_image(
    file_name: str,
    llm_multimodal: AzureChatOpenAI,
    *,
    is_example: bool = True,
) -> str:
    """Summarizes the content of a single image file.

    Args:
        file_name (str): Path to the image file.
        llm_multimodal (AzureChatOpenAI): Multimodal LLM instance.
        is_example (bool): Whether the image is an example.

    Returns:
        str: Summary of the image.

    Raises:
        InterpretationError: If the image cannot be processed.

    """
    inputs_images = read_n_convert_image(file_name)
    if not inputs_images:
        msg = f"Failed to resume image in {file_name}."
        raise InterpretationError(msg)

    res = process_images(
        [inputs_images],
        llm_multimodal=llm_multimodal,
        is_example=is_example,
    )
    return res[0]
