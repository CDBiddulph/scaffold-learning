import logging
import re
from typing import Optional

from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


ANSWER_RE = re.compile(r"Answer\s*:\s*([A-Z])", re.IGNORECASE)


def _extract_question(raw: str) -> str:
    """
    If the incoming payload contains an <input> … </input> tag (as in the training
    examples) return its contents, otherwise return the full string.
    """
    m = re.search(r"<input>(.*?)</input>", raw, flags=re.DOTALL | re.IGNORECASE)
    if m:
        question = m.group(1).strip()
        LOGGER.debug("Extracted <input> block from payload.")
        return question
    LOGGER.debug("No <input> tag found, using entire payload as question.")
    return raw.strip()


def _ask_llm(question: str, retries: int = 2) -> Optional[str]:
    """
    Ask the LLM for the answer, retrying a couple of times if we cannot parse a
    proper “Answer: X” from its reply.
    """
    system_prompt = (
        "You are an expert question-answering assistant. "
        "When you are asked a multiple-choice question, you must think step-by-step "
        "but in the end you MUST output exactly one line in the format:\n"
        "Answer: <single capital letter corresponding to the option>\n"
        "Do not output anything else on that final line."
    )

    user_prompt = f"{question}\n\nRemember: think step-by-step first, " \
                  "then end with the required 'Answer: X' line."

    for attempt in range(1, retries + 2):
        try:
            LOGGER.info("Querying LLM (attempt %d/%d)…", attempt, retries + 1)
            response = execute_llm(user_prompt, system_prompt=system_prompt)
        except Exception as exc:
            LOGGER.error("LLM query failed on attempt %d: %s", attempt, exc)
            continue

        LOGGER.debug("LLM raw response:\n%s", response)

        # Look for the answer line anywhere in the LLM output
        for line in response.splitlines()[::-1]:  # search backwards – answer likely at the end
            m = ANSWER_RE.search(line)
            if m:
                letter = m.group(1).upper()
                LOGGER.info("Parsed answer '%s' from LLM response.", letter)
                return letter

        LOGGER.warning("Could not find a valid 'Answer: <letter>' in LLM output (attempt %d).", attempt)

    LOGGER.error("Failed to obtain a valid answer from LLM after %d attempts.", retries + 1)
    return None


def process_input(input_string: str) -> str:
    """
    Main entry point required by the evaluation harness.
    Extract the question, query the LLM, parse its answer, and return ONLY the
    letter (e.g. 'B').  If anything goes wrong we default to 'A' so that we
    still return a valid option.
    """
    question_text = _extract_question(input_string)

    letter = _ask_llm(question_text)
    if letter is None:
        LOGGER.error("Falling back to default answer 'A'.")
        letter = "A"

    return letter