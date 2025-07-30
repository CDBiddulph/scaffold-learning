import re
import logging
import time
from typing import Optional

from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# --- configuration constants -------------------------------------------------
TIME_LIMIT_SECONDS = 100          # leave a safety margin vs. 120 s hard stop
LLM_TOKENS                   = 512
SYSTEM_PROMPT = (
    "You are a highly‐trained scientist who answers graduate-level multiple-choice "
    "questions spanning biology, chemistry, physics and astronomy.  Think the "
    "problem through carefully, but only reveal the single capital letter that "
    "corresponds to the correct choice.  Do NOT add any other text."
)
ANSWER_REGEXES = [
    re.compile(r"Answer\s*[:\-]?\s*([A-Z])"),
    re.compile(r"\b([A-Z])\b")           # fallback: first isolated capital letter
]


# --- helper functions ---------------------------------------------------------
def _extract_question(raw: str) -> str:
    """
    Strip the <question-metadata> block (if any) and return the actual question
    that the user wants answered.
    """
    # remove everything between <question-metadata> … </question-metadata>
    cleaned = re.sub(
        r"<question-metadata>.*?</question-metadata>",
        "",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return cleaned.strip()


def _query_llm(question: str, retries: int = 2) -> str:
    """
    Send the formatted prompt to the LLM, retrying a couple of times if we fail
    to parse a valid answer letter.
    """
    prompt = (
        f"{question}\n\n"
        "Respond with ONLY the single capital letter corresponding to the correct option."
    )
    for attempt in range(retries + 1):
        LOGGER.info("LLM attempt %d", attempt + 1)
        response = execute_llm(prompt, system_prompt=SYSTEM_PROMPT)[:LLM_TOKENS]
        letter = _parse_letter(response)
        if letter:
            LOGGER.info("Parsed answer letter %s", letter)
            return letter
        LOGGER.warning("Could not parse answer from LLM response: %r", response)
    raise ValueError("Unable to obtain a valid answer from LLM after retries.")


def _parse_letter(text: str) -> Optional[str]:
    """
    Try various regexes to find a single capital letter A–F in the LLM output.
    """
    for rx in ANSWER_REGEXES:
        m = rx.search(text)
        if m:
            letter = m.group(1)
            if letter in "ABCDEFG":
                return letter
    return None


# --- main entry point ---------------------------------------------------------
def process_input(input_string: str) -> str:
    """
    Orchestrator expected by the grading harness.
    Extracts the question, queries the LLM, and returns the answer letter.
    """
    start_time = time.time()
    try:
        question = _extract_question(input_string)
        LOGGER.debug("Question sent to LLM:\n%s", question)

        result_letter = _query_llm(question)

        elapsed = time.time() - start_time
        if elapsed > TIME_LIMIT_SECONDS:
            LOGGER.error("Processing exceeded safe-guard time limit.")
            raise TimeoutError("Time limit exceeded for processing.")

        return result_letter

    except Exception as exc:
        LOGGER.exception("process_input failed: %s", exc)
        # return an obviously invalid token so that the grader marks it wrong
        return "Z"