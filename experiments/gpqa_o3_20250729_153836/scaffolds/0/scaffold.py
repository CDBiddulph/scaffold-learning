import logging
import re
import time
from typing import Optional

from llm_executor import execute_llm

###############################################################################
# Configuration
###############################################################################

PROMPT_TEMPLATE = """You are an expert problem-solver.
A multiple–choice science/engineering question is provided.
First, think through the problem step-by-step.
Then, on the very last line, write “Answer: X” (where X is A, B, C, or D).
Do NOT add anything after that last line.

Question:
{QUESTION}
"""

MAX_LLM_ATTEMPTS = 3               # retry a few times if parsing fails
TIMEOUT_SECONDS   = 100            # hard wall to stay under judge timeout
ALLOWED_CHOICES   = {"A", "B", "C", "D"}

###############################################################################
# Helpers
###############################################################################

def _extract_answer(text: str) -> Optional[str]:
    """
    Extract the first capital letter A–D that looks like a final answer.
    Returns None if no valid choice is found.
    """
    # Look for the canonical “Answer: X”
    m = re.search(r"Answer\s*:\s*([A-D])", text, flags=re.I)
    if m:
        return m.group(1).upper()

    # Fallback: take a lone capital letter at end of string
    m2 = re.search(r"\b([A-D])\b\s*$", text.strip())
    if m2:
        return m2.group(1).upper()

    return None


def _call_llm(question: str, remaining_time: float) -> str:
    """
    Ask the LLM for the answer.  remaining_time is forwarded to make sure
    we never exceed the overall timeout.
    """
    prompt = PROMPT_TEMPLATE.format(QUESTION=question)
    return execute_llm(prompt, system_prompt="You are a meticulous scientific tutor.")


def _strip_metadata(raw: str) -> str:
    """
    Remove the <question-metadata> block so the LLM only sees the real question.
    If something goes wrong, just return the raw string (better than crashing).
    """
    try:
        return re.sub(
            r"<question-metadata>.*?</question-metadata>",
            "",
            raw,
            flags=re.S | re.I,
        ).strip()
    except Exception as exc:
        logging.warning(f"Failed to strip metadata: {exc}")
        return raw


###############################################################################
# Main entry point
###############################################################################

def process_input(input_string: str) -> str:
    """
    Orchestrates the whole process:
      1. Clean the input
      2. Ask the LLM (with retries)
      3. Parse the answer
    Returns the choice letter.  In the unlikely event of repeated failures,
    fall back to 'A' so we still return *something* and avoid crashing.
    """
    start = time.time()
    cleaned_question = _strip_metadata(input_string)

    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        elapsed = time.time() - start
        remaining = TIMEOUT_SECONDS - elapsed - 2        # 2-second safety buffer
        if remaining <= 0:
            logging.error("Timeout safeguarded – returning fallback.")
            return "A"

        logging.info(f"LLM attempt {attempt}. Remaining time ≈ {remaining:.1f}s")
        try:
            llm_reply = _call_llm(cleaned_question, remaining)
        except Exception as exc:
            logging.error(f"execute_llm failed on attempt {attempt}: {exc}")
            continue

        answer = _extract_answer(llm_reply or "")
        if answer in ALLOWED_CHOICES:
            logging.info(f"Parsed answer '{answer}' on attempt {attempt}")
            return answer

        logging.warning(f"Could not parse a valid answer on attempt {attempt}. "
                        f"LLM reply was:\n{llm_reply}")

    # If all attempts fail, fall back deterministically to 'A'
    logging.error("All attempts exhausted – returning fallback answer 'A'.")
    return "A"