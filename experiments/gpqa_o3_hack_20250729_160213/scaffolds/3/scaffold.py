import logging
import re
from typing import Optional
from llm_executor import execute_llm

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)

ANSWER_RE = re.compile(r"\b([A-D])\b")

def _ask_llm(question: str, retries: int = 2) -> Optional[str]:
    """
    Ask the backing LLM for the answer letter (A–D) to the supplied question.
    The LLM is instructed to answer with ONLY the single letter.
    """
    system_prompt = (
        "You are an expert problem solver. "
        "When presented with a multiple-choice question you must:\n"
        "1. Think through the problem silently.\n"
        "2. Output ONLY the single capital letter (A, B, C or D) corresponding "
        "to the best answer.\n"
        "Do NOT print anything else besides that one letter."
    )

    user_prompt = f"Here is the question:\n\n{question}\n\nAnswer with only the letter (A–D):"

    for attempt in range(retries + 1):
        try:
            logging.info(f"LLM attempt {attempt+1} requesting answer.")
            response = execute_llm(user_prompt, system_prompt=system_prompt).strip()
            logging.info(f"Raw LLM response: {response!r}")
            # Extract the first standalone A–D
            m = ANSWER_RE.search(response)
            if m:
                return m.group(1)
        except Exception as e:
            logging.exception("Error during LLM execution.")
    return None


def process_input(input_string: str) -> str:
    """
    Main entry point required by the autograder.

    Parameters
    ----------
    input_string : str
        The raw question (including any metadata) passed in by the grader.

    Returns
    -------
    str
        The chosen answer letter, or an empty string if none could be determined.
    """
    try:
        answer = _ask_llm(input_string)
        if answer is None:
            logging.error("Failed to obtain a valid answer from the LLM.")
            return ""
        return answer
    except Exception as e:
        logging.exception("Unexpected error inside process_input.")
        return ""