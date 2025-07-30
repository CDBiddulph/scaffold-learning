import re
import logging
from typing import Optional
from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)


def _extract_question(raw: str) -> str:
    """
    Everything between <input> … </input> is fed to the LLM.
    If those tags are missing we just pass the whole string through.
    """
    match = re.search(r"<input>(.*?)</input>", raw, re.DOTALL)
    return match.group(1).strip() if match else raw.strip()


def _llm_choose(question: str, retries: int = 2) -> Optional[str]:
    """
    Ask the LLM for the answer letter.  A couple of retries are attempted in
    case the answer is not a single A/B/C/D letter.
    """
    system = (
        "You are an expert problem solver.\n"
        "When I give you a multiple-choice question with options labeled A), B), C), D), "
        "you think carefully but in the end respond with exactly one line of the form:\n"
        "Answer: X\n"
        "where X is the single letter corresponding to the option you deem correct.\n"
        "Do NOT output anything else besides that single line."
    )

    user_prompt = (
        f"{question}\n\n"
        "Remember: after thinking internally, your entire public output MUST be exactly "
        "\"Answer: X\" (with X = A/B/C/D)."
    )

    for attempt in range(retries + 1):
        try:
            logging.info(f"LLM attempt {attempt+1}")
            response = execute_llm(user_prompt, system_prompt=system).strip()
            logging.debug(f"Raw LLM response:\n{response}")

            # Look for the first occurrence of a letter A-D (case-insensitive)
            match = re.search(r"([A-D])", response, re.I)
            if match:
                letter = match.group(1).upper()
                return f"Answer: {letter}"
        except Exception as exc:
            logging.error(f"LLM call failed on attempt {attempt+1}: {exc}")

    return None


def process_input(input_string: str) -> str:
    """
    Main entry point required by the autograder.
    """
    try:
        question_text = _extract_question(input_string)
        logging.info("Question extracted for LLM")

        result = _llm_choose(question_text)
        if result:
            return result

        logging.warning("LLM failed to deliver a usable answer; returning placeholder.")
        return "Answer: A"  # deterministic fallback

    except Exception as exc:
        logging.exception(f"Unhandled exception in process_input: {exc}")
        # Return a deterministic, recognizable string so the grader does not crash
        return "Answer: A"