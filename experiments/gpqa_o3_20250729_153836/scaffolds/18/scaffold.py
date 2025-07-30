import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
MAX_RETRIES = 3                 # How many times we'll reprompt the LLM
TIME_BUDGET_SEC = 100           # Hard stop before the 120-sec evaluator timeout
LLM_TEMPERATURE = 0.0           # We want deterministic behaviour
ANSWER_REGEX = re.compile(r"Answer:\s*([A-D])", re.IGNORECASE)

SYSTEM_PROMPT = (
    "You are an expert problem-solver. "
    "For every task you receive you must reply with exactly one line of the form:\n"
    "Answer: X\n"
    "where X is a single capital letter A, B, C or D. "
    "Do NOT add anything else, not even explanations."
)

USER_SUFFIX_INSTRUCTION = (
    "\n\nIMPORTANT:  • Think on your own first, but do NOT share your reasoning. "
    "• When you are completely sure, reply with exactly one line in the form 'Answer: <letter>'."
)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def _query_llm(prompt: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """
    Queries the LLM with the given prompt and tries to extract an answer letter.
    Returns the canonicalised answer string ('Answer: X') or None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            logging.info(f"LLM attempt {attempt}: sending prompt of {len(prompt)} characters.")
            raw_response = execute_llm(prompt, system_prompt=SYSTEM_PROMPT, temperature=LLM_TEMPERATURE)

            logging.debug(f"Raw LLM response:\n{raw_response}")

            for line in raw_response.splitlines():
                match = ANSWER_REGEX.search(line)
                if match:
                    letter = match.group(1).upper()
                    logging.info(f"Extracted answer letter '{letter}' on attempt {attempt}.")
                    return f"Answer: {letter}"

            logging.warning(f"No valid answer pattern found on attempt {attempt}.")
            # If we reach here, re-prompt by tightening instructions
            prompt = (
                "Only reply with one line exactly like 'Answer: A', 'Answer: B', 'Answer: C' or 'Answer: D'. "
                "Do not include anything else."
            )
        except Exception as e:
            logging.error(f"Error when querying LLM on attempt {attempt}: {e}", exc_info=True)

    return None

# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------
def process_input(input_string: str) -> str:
    """
    Orchestrates solving of a multiple-choice problem.
    The function MUST return a string of the exact form 'Answer: X'.
    """
    start_time = time.time()

    # Compose the user prompt we will give to the LLM
    user_prompt = input_string.strip() + USER_SUFFIX_INSTRUCTION

    answer = _query_llm(user_prompt)

    # Fallback if the LLM could not give a valid answer
    if answer is None:
        logging.error("LLM failed to return a valid answer pattern after all retries.")
        answer = "Answer: A"  # deterministic default to avoid crashing

    # Safety: make sure we are not running too long
    elapsed = time.time() - start_time
    if elapsed > TIME_BUDGET_SEC:
        logging.warning(f"process_input exceeded time budget ({elapsed:.1f}s).")

    return answer