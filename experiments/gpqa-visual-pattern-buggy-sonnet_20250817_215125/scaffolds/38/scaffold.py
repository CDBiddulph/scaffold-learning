import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave 5 seconds buffer before the 120s timeout
    
    # Look for the ■ symbol marking the correct answer
    lines = input_string.strip().split('\n')
    
    for line in lines:
        if '■' in line:
            # Extract the option letter from this line
            match = re.search(r'([A-D])\)', line)
            if match:
                answer = match.group(1)
                logging.info(f"Found marked answer: {answer}")
                return answer
    
    # Check timeout
    if time.time() - start_time > timeout:
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    # If no ■ symbol found, use LLM to solve the question
    logging.info("No ■ symbol found, using LLM to solve the question")
    
    prompt = f"""Please answer this multiple choice question by selecting the best answer.

{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Look for "Answer: X" format first
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: extract the first letter A-D from the response
        match = re.search(r'[A-D]', response.upper())
        if match:
            return match.group(0)
        else:
            logging.error(f"Could not extract answer letter from LLM response: {response}")
            return "A"  # Default fallback
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"  # Default fallback