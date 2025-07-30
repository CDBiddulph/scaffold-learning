import logging
import re
from typing import Optional
from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)


# --------------------------------------------------------------------------- #
# Helper functions                                                            #
# --------------------------------------------------------------------------- #
def _build_few_shot_prompt(question_block: str) -> str:
    """
    Builds a few-shot prompt by including a small set of solved examples
    (shown above) and then appending the new, unsolved question.  The LLM is
    instructed to mimic the format “Answer: <letter>”.
    """
    FEW_SHOT_EXAMPLES = """
<example-1>
Q: If a charge q is placed d distance away from the center of a grounded conducting sphere of radius R. Calculate the net potential energy of this system.
Options: A) U=- kq^2 d/(d^2 -R^2) | B) U=-(1/2) kq^2 R^2/(d^2 -R^2) | C) U=- (1/2) kq^2 d/(d^2 +R^2) | D) U=- (1/2) *kq^2 R/(d^2 -R^2)
A: Answer: D

<example-2>
Q: On sequencing the genome of a new fungal species, … How can the tandem duplication on chr1 be experimentally validated?
Options: A) PCR or Southern | B) Neither … | C) PCR | D) Southern
A: Answer: A

<example-3>
Q: Astronomers are studying two binary star systems … By what factor is system_1 more massive than system_2?
Options: A) ~0.7 | B) ~0.4 | C) ~1.2 | D) ~0.6
A: Answer: B

<example-4>
Q: Suppose AGNs emitted all their energy output … How are the two lines positioned with respect to each other?
Options: A) The Kerr line is above … by 5-10× | B) … 50-100× | C) below … 50-100× | D) below … 5-10×
A: Answer: A

<example-5>
Q: While studying a yeast protein X … What can you infer about X and Y?
Options: A) X operates upstream of Y | B) Y operates upstream of X | C) unrelated | D) synthetic lethal
A: Answer: A
"""
    prompt = (
        "You are a scientific reasoning assistant.  For each question decide "
        "which option (A, B, C or D) is correct.  Think step-by-step, but in "
        "the final line output only:  Answer: <letter>\n\n"
        f"{FEW_SHOT_EXAMPLES}\n"
        "<new-question>\nQ: " + question_block.strip() + "\nA:"
    )
    return prompt


def _extract_letter(llm_response: str) -> Optional[str]:
    """
    Finds the first capital letter A-D appearing after the word ‘Answer’.
    """
    match = re.search(r"Answer\s*[:\-]?\s*([ABCD])", llm_response, re.I)
    if match:
        return match.group(1).upper()
    return None


# --------------------------------------------------------------------------- #
# Main entry-point                                                            #
# --------------------------------------------------------------------------- #
def process_input(input_string: str) -> str:
    """
    1) Strip away the surrounding XML-like metadata tags (if present) and keep
       only the actual MCQ portion (question + options).
    2) Feed that to the LLM with a few-shot prompt.
    3) Parse the returned answer letter and echo it back exactly as
       “Answer: <letter>”.
    """
    try:
        # Extract everything after the first blank line (i.e., skip metadata)
        parts = re.split(r"\n\s*\n", input_string.strip(), maxsplit=1)
        question_block = parts[-1]  # take the last chunk (question text)
        prompt = _build_few_shot_prompt(question_block)

        logging.info("Sending prompt to LLM …")
        llm_response = execute_llm(prompt, system_prompt="You are a helpful assistant.")
        logging.info(f"LLM raw response:\n{llm_response}")

        letter = _extract_letter(llm_response)
        if letter is None:
            raise ValueError("Could not find answer letter in LLM response.")

        return f"Answer: {letter}"

    except Exception as exc:
        logging.error(f"process_input failed: {exc}", exc_info=True)
        # Fallback safe response (unknown)
        return "Answer: A"