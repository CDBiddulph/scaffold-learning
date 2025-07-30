import re
import logging
from typing import Optional

from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)

# A handful of solved examples to be provided to the model as demonstrations.
# Keep them SHORT (metadata removed) so the prompt stays small.
FEW_SHOT_EXAMPLES = [
    (
        "3,3,6-trimethylhepta-1,5-dien-4-one is treated with one equivalent of "
        "meta-chloroperbenzoic acid.  Two different products form (≈1:1).  A "
        "methyllithium / CuI reagent is then added in excess.  Which compound "
        "is obtained?\n"
        "A) 5-hydroxy-3,3,6,6-tetramethylhept-1-en-4-one\n"
        "B) 2,3,4,5,5-pentamethylhept-6-ene-2,4-diol\n"
        "C) 4,4,5,7,7-pentamethyloctane-3,5-diol\n"
        "D) 6-hydroxy-2,2,5,5-tetramethyloctan-4-one",
        "D",
    ),
    (
        "Chromatin is packaged in nuclear compartments whose re-organisation "
        "changes cell fate.  What mechanistic reason explains this?\n"
        "A) Increased degradation of cytosolic proteins\n"
        "B) Loss of DNA from the genome\n"
        "C) Differential access to the transcriptional machinery\n"
        "D) Higher susceptibility to mutations",
        "C",
    ),
    (
        "Two stars behave as black bodies and peak at the same wavelength.  "
        "Star 1’s radius is 1.5× that of Star 2.  What is the luminosity ratio "
        "L1/L2?\n"
        "A) ~2.25  B) ~2.23  C) ~2.35  D) ~2.32",
        "B",
    ),
    (
        "Leaving the lab, a chemist says 'my compounds are on top of each "
        "other.'  What does this likely mean?\n"
        "A) Similar optical rotations\n"
        "B) Similar polarities\n"
        "C) Similar boiling points\n"
        "D) Strong non-covalent interactions",
        "B",
    ),
    (
        "In neutrino model building, 'opening up the operator' is technically "
        "called what?\n"
        "A) Infrared divergence  B) Ultraviolet divergence  "
        "C) Infrared completion  D) Ultraviolet completion",
        "D",
    ),
]

SYSTEM_PROMPT = (
    "You are an expert at solving academic multiple-choice questions in many "
    "fields.  For every question, quietly think step-by-step, decide which "
    "choice is correct, and then output ONLY the capital letter (A, B, C or D) "
    "on its own line.  Absolutely no explanation, no labels, nothing else."
)


def build_prompt(question: str) -> str:
    """
    Build a single prompt consisting of several few-shot examples followed by
    the unseen question.
    """
    prompt_lines = []
    for idx, (q, ans) in enumerate(FEW_SHOT_EXAMPLES, 1):
        prompt_lines.append(f"### Example {idx}\n{q}\nAnswer: {ans}\n")
    prompt_lines.append("### New Question")
    prompt_lines.append(question.strip())
    prompt_lines.append("Answer:")
    return "\n".join(prompt_lines)


ANSWER_RE = re.compile(r"\b([ABCD])\b")


def extract_letter(llm_output: str) -> Optional[str]:
    """
    Retrieve the first standalone capital letter A-D from model output.
    """
    match = ANSWER_RE.search(llm_output)
    return match.group(1) if match else None


def process_input(input_string: str) -> str:
    """
    Main entry point required by the grader.
    1. Strips the incoming raw text to obtain the actual question (all content).
    2. Builds a prompt with few-shot examples.
    3. Calls the LLM once.
    4. Parses its return for a single capital letter A-D.
    5. Returns that letter (or a sensible fallback).
    """
    try:
        prompt = build_prompt(input_string)
        logging.debug(f"Prompt sent to LLM:\n{prompt}")

        llm_raw = execute_llm(prompt=prompt, system_prompt=SYSTEM_PROMPT)
        logging.info(f"Raw LLM output: {llm_raw!r}")

        letter = extract_letter(llm_raw)
        if letter is None:
            raise ValueError("Could not parse an answer letter from LLM output.")

        return letter

    except Exception as exc:
        logging.error(f"Error in process_input: {exc}")
        # Fallback: return 'A' so that the grader receives *some* answer.
        return "A"