import logging
import os
import re
import time
from typing import Optional

from llm_executor import execute_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

TIMEOUT_SECONDS = 100  # Leave some buffer before the judge-imposed 120 s limit


def _query_llm(question: str, retries: int = 2) -> str:
    """
    Ask the LLM to solve a single multiple-choice problem and return its raw response.
    It is prompted to give ONLY the letter of the correct alternative (A/B/C/D).
    """
    system_prompt = (
        "You are a world-class subject-matter expert. "
        "You will be given a multiple-choice question with four choices labelled A-D. "
        "Think step-by-step internally, but DO NOT reveal your reasoning. "
        "Your final output must be exactly one capital letter (A, B, C, or D) with no extra characters."
    )

    user_prompt = f"{question}\n\nONLY output the single correct letter."
    for attempt in range(retries + 1):
        try:
            response = execute_llm(user_prompt, system_prompt=system_prompt).strip()
            if re.fullmatch(r"[ABCD]", response):
                return response
            logging.warning(f"Attempt {attempt}: Unexpected LLM output -> {response!r}")
        except Exception as exc:
            logging.error(f"LLM execution failed on attempt {attempt}: {exc}", exc_info=True)
        time.sleep(0.5)  # brief back-off
    # Fallback: pick the most common correct answer historically (B) if everything fails
    logging.error("LLM failed to provide a valid answer; falling back to 'B'.")
    return "B"


def _extract_question_body(raw: str) -> str:
    """
    Strip the leading XML-like metadata tags so that the LLM only sees the human-readable
    portion of the question.
    """
    # Remove everything up to the first blank line after </question-metadata>
    split_token = "</question-metadata>"
    if split_token in raw:
        raw = raw.split(split_token, 1)[1]
    return raw.strip()


def process_input(input_string: str) -> str:
    """
    Main entry point required by the grader.
    Receives the full prompt, extracts the actual question, queries the LLM,
    and returns the single-letter answer.
    """
    start_time = time.time()
    try:
        question_text = _extract_question_body(input_string)
        logging.info("Question extracted and sent to LLM for solving.")
        answer = _query_llm(question_text)
        elapsed = time.time() - start_time
        logging.info(f"Answered in {elapsed:.2f}s – returning {answer}")
        return answer
    except Exception as exc:
        logging.exception(f"Unexpected failure in process_input: {exc}")
        # Absolute last-ditch fallback
        return "B"