import logging
import re
import signal
from contextlib import contextmanager
from typing import Optional

from llm_executor import execute_llm

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
LOGGER_NAME = "question_solver"
TIMEOUT_SECONDS = 90          # hard time-cap for the LLM call
LLM_TOKENS_MAX = 512          # token budget we tell the LLM to stay within
MODEL_SYSTEM_PROMPT = (
    "You are a brilliant academic who excels at quantitative reasoning, "
    "physics, chemistry, biology, mathematics, astronomy, and general science. "
    "Given a multiple-choice question you will silently work out the solution "
    "step-by-step, then output ONLY the single capital letter (A, B, C or D) "
    "corresponding to the best answer.  Do NOT output anything else."
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(LOGGER_NAME)


class TimeoutException(Exception):
    """Raised when execution exceeds a preset time limit."""


@contextmanager
def time_limit(seconds: int):
    """Context-manager that raises TimeoutException after *seconds*."""
    def signal_handler(signum, frame):
        raise TimeoutException(f"Timed out after {seconds} seconds.")

    original_handler = signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)                    # cancel alarm
        signal.signal(signal.SIGALRM, original_handler)


def _ask_llm(question: str) -> str:
    """
    Send *question* to the LLM and return raw response.
    A short, precise prompt keeps the model focussed.
    """
    user_prompt = (
        f"{question}\n\n"
        f"Remember: ONLY output a single letter (A, B, C, or D).\n"
        f"(Max {LLM_TOKENS_MAX} tokens.)"
    )

    logger.info("Calling LLM …")
    with time_limit(TIMEOUT_SECONDS):
        response = execute_llm(
            prompt=user_prompt,
            system_prompt=MODEL_SYSTEM_PROMPT
        )
    logger.info("LLM call completed.")
    return response.strip()


def _extract_letter(text: str) -> Optional[str]:
    """
    Find the first standalone capital letter A–D in *text*.
    Returns None if not found.
    """
    match = re.search(r"\b([ABCD])\b", text)
    return match.group(1) if match else None


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def process_input(input_string: str) -> str:
    """
    Main entry-point required by the autograder.
    Receives the entire problem statement in *input_string* and must return the
    chosen answer letter (A/B/C/D).  All heavy lifting is delegated to the LLM.
    """
    if not input_string or not input_string.strip():
        logger.error("Empty input received by process_input().")
        return ""

    try:
        raw_response = _ask_llm(input_string)
    except TimeoutException as e:
        logger.error(str(e))
        return ""
    except Exception as exc:
        logger.exception("LLM call failed.")
        return ""

    letter = _extract_letter(raw_response)
    if letter is None:
        # If parsing failed, log and fall back to the raw response (trimmed).
        logger.warning(f"Could not parse answer letter from LLM output: {raw_response!r}")
        return raw_response.strip()

    logger.info(f"Predicted answer: {letter}")
    return letter