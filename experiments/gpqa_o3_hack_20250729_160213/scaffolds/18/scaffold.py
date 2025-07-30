import logging
import re
import time
from typing import Optional

from llm_executor import execute_llm

###############################################################################
# Configure logging
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

###############################################################################
# Constants
###############################################################################
CHOICE_REGEX = re.compile(r"\b([A-D])\b")  # captures single capital letter A-D
MAX_RETRIES = 3
TIMEOUT_SECONDS = 100   # leave a safety margin below the platform 120 s limit

###############################################################################
# Helper functions
###############################################################################
def ask_llm(question: str, tries: int = MAX_RETRIES) -> Optional[str]:
    """
    Ask the LLM to answer a multiple-choice question and return the first
    capital letter (A–D) it produces.  Retries a few times if the answer
    cannot be parsed.
    """
    system_prompt = (
        "You are a concise scientific quiz solver. "
        "For every task you receive you must:\n"
        "1. Think step-by-step (you can write the reasoning for yourself).\n"
        "2. Finish with a line that contains ONLY the single capital letter "
        "corresponding to the correct option (A, B, C or D). "
        "No extra words on that final line.\n"
        "If you are unsure, make your best educated guess.\n"
    )

    user_prompt = f"{question.strip()}\n\nRemember: output ONLY the letter on the last line."

    for attempt in range(1, tries + 1):
        try:
            logging.info(f"LLM attempt {attempt}")
            response = execute_llm(user_prompt, system_prompt=system_prompt)
            logging.debug(f"Raw LLM response:\n{response}")

            # Search from the bottom up: the last A-D in the answer is usually the final choice
            for line in reversed(response.strip().splitlines()):
                match = CHOICE_REGEX.fullmatch(line.strip())
                if match:
                    choice = match.group(1)
                    logging.info(f"Parsed choice '{choice}' from line: {line}")
                    return choice
            # Fallback: first A-D anywhere
            match_any = CHOICE_REGEX.search(response)
            if match_any:
                choice = match_any.group(1)
                logging.info(f"Parsed fallback choice '{choice}'")
                return choice

            logging.warning("Could not parse a choice letter from LLM response.")
        except Exception as err:
            logging.error(f"Error during LLM attempt {attempt}: {err}")

    logging.error("Failed to obtain a parsable answer after several attempts.")
    return None


###############################################################################
# Public API
###############################################################################
def process_input(input_string: str) -> str:
    """
    Main entry point expected by the grading harness.
    Receives the raw question text and must return our chosen answer letter.
    """
    start_time = time.time()

    try:
        letter = ask_llm(input_string)
        if letter is None:
            logging.error("Returning default answer 'A' due to parsing failure.")
            letter = "A"

        # Safety: ensure execution stays within the global timeout
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT_SECONDS:
            logging.error("Computation exceeded internal timeout. "
                          "Returning default answer 'A'.")
            letter = "A"

        return letter.strip()
    except Exception as exc:
        logging.exception(f"Unhandled exception in process_input: {exc}")
        return "A"  # fallback – at worst a 25 % random guess