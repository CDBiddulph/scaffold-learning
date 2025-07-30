import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

################################################################################
# Helper functions
################################################################################
def _strip_xml_metadata(text: str) -> str:
    """
    Remove the <question-metadata> … </question-metadata> block if present
    and return the remainder (i.e. the actual question shown to the user).
    """
    cleaned = re.sub(r"<question-metadata>.*?</question-metadata>", "", text, flags=re.S)
    return cleaned.strip()


def _extract_answer_letter(llm_raw: str) -> Optional[str]:
    """
    Look for a single capital letter (A–D) that represents the chosen answer.

    We accept formats such as:
      "Answer: B"
      "B"
      "The correct answer is (C)"
      etc.
    """
    match = re.search(r"\b([A-D])\b", llm_raw)
    if match:
        return match.group(1)
    return None


def _query_llm(question: str, max_tries: int = 2) -> str:
    """
    Ask the LLM for the answer.  We try a couple of times if parsing fails.
    """
    SYSTEM = (
        "You are an expert teaching assistant.  "
        "Read the multiple-choice science question provided by the user, "
        "think step-by-step, and then reply with exactly one line of the form:\n"
        "Answer: <letter>\n"
        "where <letter> is A, B, C, or D.  No other text, no code fencing."
    )

    USER_TEMPLATE = (
        "{q}\n\n"
        "Think step-by-step to explain your reasoning, then give the final answer."
    )

    for attempt in range(1, max_tries + 1):
        try:
            prompt = USER_TEMPLATE.format(q=question)
            logger.info(f"Calling LLM (attempt {attempt})")
            raw = execute_llm(prompt, system_prompt=SYSTEM).strip()
            letter = _extract_answer_letter(raw)
            if letter:
                logger.info(f"LLM answer parsed as {letter}")
                return f"Answer: {letter}"
            else:
                logger.warning(f"Failed to parse answer letter from LLM output: {raw!r}")
        except Exception as exc:
            logger.error(f"LLM call failed on attempt {attempt}: {exc}")

    # If everything failed, indicate we could not determine an answer
    return "ERROR"


################################################################################
# Public API
################################################################################
def process_input(input_string: str) -> str:
    """
    Main entry point expected by the autograder.
    Extract the actual question text and delegate to the LLM.
    """
    start = time.time()

    try:
        question_text = _strip_xml_metadata(input_string)
        logger.debug(f"Question extracted:\n{question_text}")

        # Bail early if we somehow have no question left
        if not question_text:
            return "ERROR"

        result = _query_llm(question_text)

        # Make sure we do not exceed the time limit
        if time.time() - start > 115:
            logger.warning("Approaching timeout; returning current result.")
        return result

    except Exception as exc:
        logger.exception(f"Unexpected failure in process_input: {exc}")
        return "ERROR"