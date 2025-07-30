import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
PROMPT_TEMPLATE = """You are an expert tutor.
1. Read the following multiple-choice problem.
2. Think about it step-by-step (show your chain of thought).
3. On the very last line, write the final choice in the exact format:
Answer: <letter>

Problem:
{question}
"""
SYSTEM_PROMPT = (
    "You are a careful problem-solver. "
    "Always give the reasoning first, then a line with "
    "\"Answer: <letter>\" and nothing else on that last line."
)

TIMEOUT_BUFFER = 10          # seconds reserved so we never overrun
LLM_MAX_RETRIES = 2          # how many times we’ll re-query the LLM on failure
LLM_TOKENS = 700             # rough upper bound for the answer size
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def _extract_question(text: str) -> str:
    """
    Remove the <question-metadata> block (if present) so the LLM only sees the
    human-readable statement + options.
    """
    cleaned = re.sub(r"<question-metadata>.*?</question-metadata>", "", text, flags=re.S)
    # strip outer tags such as <input> if present
    cleaned = re.sub(r"</?input>", "", cleaned, flags=re.I)
    return cleaned.strip()


def _ask_llm(question: str) -> str:
    """
    Query the LLM and return its raw response.
    If the model doesn't end with the required 'Answer: X' line,
    retry a limited number of times with a clarifying reminder.
    """
    for attempt in range(LLM_MAX_RETRIES + 1):
        logging.info(f"Querying LLM (attempt {attempt + 1})")
        response = execute_llm(
            prompt=PROMPT_TEMPLATE.format(question=question),
            system_prompt=SYSTEM_PROMPT,
        )

        if _extract_choice(response) is not None:
            return response

        # if failed, prepend a terse reminder and try once more
        reminder = (
            "REMINDER: Finish your answer with ONLY one line exactly like "
            "\"Answer: A\" (or B/C/D). Let's try again.\n\n"
        )
        PROMPT_WITH_REMINDER = reminder + PROMPT_TEMPLATE.format(question=question)
        question = question  # unchanged
    return response  # return last attempt even if malformed


def _extract_choice(response: str) -> Optional[str]:
    """
    Find the final answer line and extract the letter.
    """
    match = re.search(r"Answer:\s*([A-D])\b", response.strip(), re.I)
    if match:
        return match.group(1).upper()
    return None


def process_input(input_string: str) -> str:
    """
    Main entry point expected by the grading harness.
    Receives raw input, returns 'Answer: X'.
    """
    start_time = time.time()
    try:
        question = _extract_question(input_string)

        # Safety check for runtime
        if time.time() - start_time > (120 - TIMEOUT_BUFFER):
            raise TimeoutError("Approaching overall timeout before LLM call.")

        llm_response = _ask_llm(question)
        choice = _extract_choice(llm_response)

        if choice:
            return f"Answer: {choice}"

        # If we still couldn't parse, fall back: guess the most common answer (A)
        logging.error("Could not parse LLM response for final answer. Falling back to 'A'.")
        return "Answer: A"

    except Exception as exc:
        logging.exception(f"Unexpected error: {exc}")
        # Fallback graceful degradation
        return "Answer: A"