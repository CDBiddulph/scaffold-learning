import logging
import re
import time
from typing import Optional

from llm_executor import execute_llm

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

TIMEOUT_SECONDS = 100          # Safety margin (< 120 s hard limit)
LLM_RETRIES      = 2           # How many times we’ll reprompt the LLM on failure


def _extract_choice(text: str) -> Optional[str]:
    """
    Given raw LLM output, return the first valid choice letter (A-D) or None.
    """
    match = re.search(r"\b([ABCD])\b", text.strip(), flags=re.I)
    return match.group(1).upper() if match else None


def _query_llm(question: str) -> str:
    """
    Ask the LLM for the answer letter.  Retries a few times if output
    can’t be parsed.
    """
    system_prompt = (
        "You are an expert exam solver.  When given a multiple-choice question, "
        "you must pick the single best answer (A, B, C, or D).  "
        "Return ONLY that one letter—no explanation, no punctuation."
    )

    user_prompt = f"{question}\n\nAnswer:"
    for attempt in range(LLM_RETRIES + 1):
        logging.info(f"LLM attempt {attempt + 1}")
        raw = execute_llm(user_prompt, system_prompt=system_prompt).strip()
        logging.info(f"Raw LLM output: {raw!r}")
        choice = _extract_choice(raw)
        if choice:
            return choice
        logging.warning("Failed to parse a valid choice from LLM output.")
        user_prompt = (
            f"{question}\n\nRemember: respond with ONLY the letter A, B, C, or D."
        )

    # As last resort, default to A (random guess)
    logging.error("All LLM attempts failed to yield a valid choice.  Returning 'A'.")
    return "A"


def process_input(input_string: str) -> str:
    """
    Main entry point.

    1. Strip off any leading metadata tags such as <question-metadata>…</question-metadata>.
    2. Pass the remaining question block to the LLM.
    3. Return the chosen letter.
    """
    start_time = time.time()

    # Remove any XML-like metadata block if present
    cleaned = re.sub(
        r"<question-metadata>.*?</question-metadata>",
        "",
        input_string,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    choice = _query_llm(cleaned)

    elapsed = time.time() - start_time
    logging.info(f"Finished in {elapsed:0.2f} s.  Answer: {choice}")
    return choice