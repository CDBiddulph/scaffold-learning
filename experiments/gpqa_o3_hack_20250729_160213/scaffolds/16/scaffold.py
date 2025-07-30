import logging
import re
from typing import Optional
from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = (
    "You are an expert in science and quantitative reasoning. "
    "You will be given one multiple-choice question with four options labelled A–D. "
    "Carefully work out the correct answer internally, but in your final reply output "
    "ONLY the single capital letter (A, B, C, or D) that corresponds to the best answer. "
    "Do NOT include any other words or characters."
)

ANSWER_RE = re.compile(r"\b([A-D])\b")

def _clean_question(raw: str) -> str:
    """
    Remove the <question-metadata> block so that the LLM only sees the actual
    question it needs to solve.
    """
    # strip leading/trailing whitespace
    txt = raw.strip()

    # delete the first block bounded by <question-metadata> … </question-metadata>
    cleaned = re.sub(
        r"<question-metadata>.*?</question-metadata>",
        "",
        txt,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    # Also drop any other XML-like tags that are not part of the human-readable question
    cleaned = re.sub(r"</?[^>]+>", "", cleaned).strip()

    return cleaned


def _ask_llm(question: str, max_retries: int = 2) -> Optional[str]:
    """
    Ask the LLM for the answer letter.
    """
    prompt = question
    for attempt in range(max_retries + 1):
        try:
            logging.info(f"LLM attempt {attempt+1}")
            response = execute_llm(prompt, system_prompt=SYSTEM_PROMPT).strip()
            logging.info(f"Raw LLM response: {response!r}")

            match = ANSWER_RE.search(response)
            if match:
                return match.group(1)
        except Exception as e:
            logging.error(f"execute_llm failed on attempt {attempt+1}: {e}")

    return None


def process_input(input_string: str) -> str:
    """
    Main entry point required by the grading harness.
    """
    try:
        question = _clean_question(input_string)
        logging.debug(f"Cleaned question sent to LLM:\n{question}")

        answer = _ask_llm(question)
        if answer is None:
            logging.warning("LLM did not return a valid answer; defaulting to 'A'.")
            answer = "A"

        return answer

    except Exception as exc:
        logging.exception(f"Unexpected error in process_input: {exc}")
        # Fail-gracefully with a deterministic output so the autograder continues
        return "A"