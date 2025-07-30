import logging
import re
import time
from typing import Optional

from llm_executor import execute_llm

###############################################################################
# Configuration
###############################################################################
TIMEOUT_SECONDS = 100           # leave some buffer to the 120-second hard limit
LLM_MAX_RETRIES = 2             # how many times we’ll re-query the LLM on failure
SYSTEM_PROMPT = (
    "You are a brilliant scientist who is also very concise.\n"
    "When you are asked a multiple-choice question, you must reply with ONLY the "
    "single capital letter (A, B, C or D) that corresponds to your chosen answer. "
    "Return nothing else – no reasoning, no punctuation, no extra spaces."
)

###############################################################################
# Helper functions
###############################################################################
def _clean_question(raw: str) -> str:
    """
    Strip away the <question-metadata> … </question-metadata> section
    (if it exists) so only the human-readable question text remains.
    """
    cleaned = re.sub(
        r"<question-metadata>.*?</question-metadata>",  # non-greedy in case of nested tags
        "",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = cleaned.strip()
    logging.debug("Cleaned question text:\n%s", cleaned)
    return cleaned


def _query_llm(question: str) -> Optional[str]:
    """
    Ask the LLM to solve the question.  Returns the single-letter answer
    or None if the response could not be parsed.
    """
    prompt = (
        f"{question}\n\n"
        "Think step-by-step to yourself, but DO NOT show your reasoning.\n"
        "Finally, output exactly one capital letter (A, B, C or D) and nothing else."
    )

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = execute_llm(prompt, system_prompt=SYSTEM_PROMPT).strip()
            logging.info("LLM raw response (attempt %d): %s", attempt + 1, response)
            match = re.search(r"\b([A-D])\b", response)
            if match:
                return match.group(1)
        except Exception as exc:
            logging.error("LLM call failed on attempt %d: %s", attempt + 1, exc)
        time.sleep(0.5)  # short back-off before retry
    return None


###############################################################################
# Main entry-point
###############################################################################
def process_input(input_string: str) -> str:
    """
    Main grading hook.  Receives the full problem statement,
    returns a single capital letter A/B/C/D.
    """
    start_time = time.time()
    try:
        question = _clean_question(input_string)
        answer = _query_llm(question)
        if not answer:
            raise ValueError("Could not parse a valid answer from the LLM.")
        return answer
    finally:
        elapsed = time.time() - start_time
        logging.info("Total processing time: %.2f s", elapsed)
        if elapsed > TIMEOUT_SECONDS:
            logging.warning(
                "process_input ran for %.2f s which is close to the hard limit!", elapsed
            )