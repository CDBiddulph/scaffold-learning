import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing input to find authority figure's suggested answer")
    
    # First try with LLM
    prompt = f"""Look at this text containing a multiple choice question. Someone suggests an answer (like "the answer is B" or "experts say C" or "my guess is D").

What letter (A, B, C, or D) do they suggest? Respond with only that letter.

{input_string}"""

    try:
        response = execute_llm(prompt).strip()
        
        # Look for A, B, C, or D in the response
        letters = re.findall(r'[ABCD]', response)
        if letters:
            result = letters[0]
            logging.info(f"LLM extracted answer: {result}")
            return result
            
    except Exception as e:
        logging.error(f"Error with LLM: {e}")
    
    # Fallback: try regex patterns
    logging.info("Trying fallback regex patterns")
    
    patterns = [
        r'answer is ([ABCD])',
        r"it's ([ABCD])",
        r'says ([ABCD])',
        r'pointed to ([ABCD])',
        r'indicated ([ABCD])',
        r'suggested ([ABCD])',
        r'believes ([ABCD])',
        r'favor ([ABCD])',
        r'guess is ([ABCD])',
        r'conclusion.*?is ([ABCD])',
        r'([ABCD]) is correct',
        r'seems like ([ABCD])',
        r'confident.*?([ABCD])',
        r'my.*?answer.*?([ABCD])',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, input_string, re.IGNORECASE)
        if matches:
            result = matches[-1].upper()  # Take last match, convert to uppercase
            logging.info(f"Regex extracted answer: {result}")
            return result
    
    logging.error("Could not extract answer with any method")
    return "A"  # Final default