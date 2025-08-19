import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Try to find the line marked with ■
    for line in input_string.split('\n'):
        # Look for ■ followed by a letter and )
        if '■' in line:
            match = re.search(r'([A-D])\)', line)
            if match:
                answer = match.group(1)
                logging.info(f"Found marked answer: {answer}")
                return answer
    
    # Check timeout before expensive LLM call
    if time.time() - start_time > 100:  # Leave 20 seconds buffer
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    # If we didn't find a marked answer, try to use the LLM to solve the question
    logging.warning("No marked answer found, attempting to solve using LLM")
    
    prompt = f"""You are given a multiple choice question. Please analyze it carefully and return only the letter of the correct answer (A, B, C, or D).

{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
    
    try:
        response = execute_llm(prompt)
        # Look for "Answer: X" pattern in the response
        answer_match = re.search(r'Answer:\s*([A-D])', response)
        if answer_match:
            answer = answer_match.group(1)
            logging.info(f"LLM provided answer: {answer}")
            return answer
        else:
            logging.error(f"Could not parse answer from LLM response: {response}")
            return "A"  # Default fallback
    except Exception as e:
        logging.error(f"Error using LLM: {e}")
        return "A"  # Default fallback