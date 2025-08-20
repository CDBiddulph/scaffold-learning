import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    # First, check if there's already a marked answer with ■
    marked_match = re.search(r'■\s*([A-D])\)', input_string)
    if marked_match:
        answer = marked_match.group(1)
        logging.info(f"Found marked answer: {answer}")
        return answer
    
    # No marked answer found, solve using LLM
    logging.info("No marked answer found, solving with LLM")
    
    prompt = f"""You are answering a multiple choice question. Read the question carefully and think step-by-step. Then give your final answer in the exact format "Answer: <letter>" where <letter> is A, B, C, or D.

{input_string}"""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback: look for final letter pattern in the response
        lines = response.strip().split('\n')
        for line in reversed(lines):
            if line.strip():
                # Look for patterns like "A)", "B)", etc.
                letter_match = re.search(r'\b([A-D])\)', line)
                if letter_match:
                    answer = letter_match.group(1)
                    logging.info(f"Extracted answer from line: {answer}")
                    return answer
                # Look for just the letter
                letter_match = re.search(r'\b([A-D])\b', line)
                if letter_match:
                    answer = letter_match.group(1)
                    logging.info(f"Extracted letter from line: {answer}")
                    return answer
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
    
    # If all else fails, return A as default
    logging.warning("Could not extract answer, defaulting to A")
    return "A"