import logging
import re
from typing import Optional
from llm_executor import execute_llm

logging.basicConfig(level=logging.INFO)
LETTER_PATTERN = re.compile(r"\b([A-D])\b")

# A handful of solved examples to steer the model
FEW_SHOT = """
Below are examples of how you should reason and, at the end, output ONLY the single capital letter that corresponds to the correct choice.

Example 1
----------
<question>
Identify the final product produced when cyclobutyl(cyclopropyl)methanol reacts with phosphoric acid in water.

A) 1,2,3,4,5,6-hexahydropentalene
B) 1,2-dimethylcyclohexa-1,4-diene
C) spiro[3.4]oct-5-ene
D) [1,1'-bi(cyclobutan)]-1-ene
</question>
Thoughts: The reaction is a pinacol rearrangement that contracts / expands rings … (detailed reasoning omitted for brevity).
Answer: A

Example 2
----------
<question>
Racemic 3-methylpent-1-ene is treated with Grubbs catalyst. How many possible products are there (excluding ethene)?

A) 2
B) 4
C) 6
D) 8
</question>
Thoughts: Cross-metathesis & self-metathesis produce … (reasoning).
Answer: C

Example 3
----------
<question>
The water and oil contact angles on a smooth clean glass surface are 65° and 40° respectively. The surface of this same piece of glass is then modified by treatment with a CF₄ plasma. What would be the best estimate of the water and oil contact angles on the treated surface?

A) Water = 122°, Oil = 18°
B) Water = 104°, Oil = 122°
C) Water = 37°, Oil = 18°
D) Water = 122°, Oil = 104°
</question>
Thoughts: Fluorination greatly increases hydrophobicity while also increasing oleophobicity but to a lesser extent …
Answer: D

Remember: after thinking, output ONLY the single capital letter (A, B, C, or D). Do NOT output anything else.
"""

def _ask_llm(question_text: str, max_attempts: int = 2) -> Optional[str]:
    """
    Ask the LLM to solve the question.  Returns a single letter A–D or None.
    """
    prompt = (
        FEW_SHOT
        + "\n\nNew question\n------------\n<question>\n"
        + question_text.strip()
        + "\n</question>\nAnswer:"
    )

    for attempt in range(1, max_attempts + 1):
        try:
            logging.info(f"LLM attempt {attempt}")
            raw = execute_llm(prompt)
            # Search the first standalone capital letter A–D
            match = LETTER_PATTERN.search(raw)
            if match:
                letter = match.group(1)
                logging.info(f"Parsed answer letter: {letter}")
                return letter
            else:
                logging.warning(f"Attempt {attempt}: Could not find answer letter in LLM output:\n{raw}")
        except Exception as e:
            logging.error(f"LLM attempt {attempt} failed with exception: {e}")
    return None

def _extract_question(input_string: str) -> str:
    """
    Remove the <question-metadata> tag (if present) to leave only the user-visible question.
    """
    # Delete everything between <question-metadata> and </question-metadata>
    cleaned = re.sub(
        r"<question-metadata>.*?</question-metadata>",
        "",
        input_string,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return cleaned.strip()

def process_input(input_string: str) -> str:
    """
    Main entry point.  Returns just the answer letter, or an empty string on failure.
    """
    question = _extract_question(input_string)
    logging.debug(f"Question sent to LLM:\n{question}")

    answer = _ask_llm(question)
    if answer is None:
        logging.error("Failed to obtain valid answer from LLM; returning empty string.")
        return ""
    return answer