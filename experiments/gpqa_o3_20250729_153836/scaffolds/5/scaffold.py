import logging
import re
import time
from typing import Optional

from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

TIME_LIMIT_SECONDS = 110          # leave a safety margin vs. 120-s hard limit
LLM_MAX_RETRIES     = 2           # total = 1 initial try + 2 retries


def _extract_choice(text: str) -> Optional[str]:
    """
    Look for a single capital letter A-D that seems to be the model’s final choice.
    Priority:
      1)  FINAL_ANSWER: X
      2)  Answer: X
      3)  the last standalone capital letter A-D
    """
    # 1)  FINAL_ANSWER: X
    m = re.search(r"FINAL_ANSWER\s*:\s*([ABCD])", text, flags=re.I)
    if m:
        return m.group(1).upper()

    # 2)  Answer: X
    m = re.search(r"Answer\s*:\s*([ABCD])", text, flags=re.I)
    if m:
        return m.group(1).upper()

    # 3)  last standalone capital letter A-D
    letters = re.findall(r"\b([ABCD])\b", text)
    if letters:
        return letters[-1]

    return None


def _ask_llm(question: str) -> str:
    """
    Query the LLM with a careful prompt.  The model is instructed to keep its
    chain-of-thought hidden and finish with   FINAL_ANSWER: <letter>
    """
    system_prompt = (
        "You are a careful expert solver of multiple-choice science problems.\n"
        "Think problems through thoroughly, but DO NOT reveal your reasoning.\n"
        "Instead, after finishing your private reasoning, output one line only:\n"
        "FINAL_ANSWER: <letter>\n"
        "where <letter> is A, B, C, or D.  No other words."
    )

    user_prompt = (
        f"{question}\n\n"
        "Remember: only output the final line 'FINAL_ANSWER: <letter>'."
    )

    return execute_llm(user_prompt, system_prompt=system_prompt)


def process_input(input_string: str) -> str:
    """
    Main entry point required by the autograder.
    Receives the whole question blob and must return the chosen letter.
    """
    start_time = time.time()
    last_error = None

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            if time.time() - start_time > TIME_LIMIT_SECONDS:
                raise TimeoutError("Approaching global time limit, aborting.")

            LOGGER.info(f"LLM attempt {attempt + 1}")
            raw_response = _ask_llm(input_string)
            LOGGER.debug(f"LLM raw response:\n{raw_response}")

            choice = _extract_choice(raw_response or "")
            if choice in {"A", "B", "C", "D"}:
                LOGGER.info(f"Parsed choice: {choice}")
                return choice

            raise ValueError(f"Could not parse a valid choice from LLM output: {raw_response!r}")

        except Exception as exc:        # catch *everything* so we can retry
            last_error = exc
            LOGGER.warning(f"Attempt {attempt + 1} failed: {exc}")

    # If we reach here, every attempt failed.  Log and raise the last error.
    LOGGER.error(f"All attempts failed. Last error: {last_error}")
    # Return a dummy answer to avoid crashing the evaluator; statistically choose 'A'
    return "A"