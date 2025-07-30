import logging
import re
import time
from typing import Optional

from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


ANSWER_PATTERN = re.compile(r"\b([ABCD])\b")


def _call_llm(question: str, retries: int = 2, temperature: float = 0.2) -> Optional[str]:
    """
    Ask the LLM to answer the multiple-choice question.
    We explicitly instruct it to finish with a single capital letter (A–D).
    """
    system_prompt = (
        "You are an expert problem-solver.  Carefully work through any problem you are given. "
        "However, after your reasoning you MUST output ONLY the single capital letter "
        "(A, B, C, or D) corresponding to your final choice on its own line. "
        "No additional words, no punctuation."
    )

    user_prompt = (
        f"{question.strip()}\n\n"
        "Think step-by-step, but remember: your final output must be exactly one of "
        "A, B, C, or D on its own line."
    )

    for attempt in range(retries + 1):
        try:
            LOGGER.info("Querying LLM (attempt %d)…", attempt + 1)
            raw_response = execute_llm(user_prompt, system_prompt=system_prompt)
        except Exception as exc:
            LOGGER.error("LLM execution failed on attempt %d: %s", attempt + 1, exc)
            continue

        LOGGER.debug("LLM raw response:\n%s", raw_response)

        # Search from the bottom for the first standalone capital letter A–D
        for line in reversed(raw_response.strip().splitlines()):
            line = line.strip()
            if ANSWER_PATTERN.fullmatch(line):
                return line
        LOGGER.warning("Could not find answer letter in LLM response on attempt %d.", attempt + 1)

    return None


def extract_question_body(input_string: str) -> str:
    """
    Remove the <question-metadata> block (if present) and everything after </question-metadata>.
    What remains should be the actual question the LLM needs.
    """
    # remove metadata tags and their content
    cleaned = re.sub(r"<question-metadata>.*?</question-metadata>", "", input_string, flags=re.S)
    # remove any <timeout>…</timeout> section
    cleaned = re.sub(r"<timeout>.*?</timeout>", "", cleaned, flags=re.S)
    return cleaned.strip()


def process_input(input_string: str) -> str:
    """
    Main entry point required by the grader.
    Receives the full task description (including metadata),
    returns the single-letter answer (A–D) predicted by the LLM.
    """
    start_time = time.time()
    try:
        question_text = extract_question_body(input_string)

        LOGGER.info("Extracted question (first 120 chars): %s…", question_text[:120].replace("\n", " "))

        answer_letter = _call_llm(question_text)

        if answer_letter is None:
            LOGGER.error("LLM failed to provide a valid answer after all retries.")
            return ""  # empty string => graded as incorrect but avoids crash

        elapsed = time.time() - start_time
        LOGGER.info("Answered '%s' in %.2f s", answer_letter, elapsed)
        return answer_letter

    except Exception as e:
        LOGGER.exception("Unhandled error in process_input: %s", e)
        return ""