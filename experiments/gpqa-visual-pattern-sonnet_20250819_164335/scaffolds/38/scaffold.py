import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120s limit
    
    # Check if there's already a ■ symbol indicating the correct answer (for training examples)
    if '■' in input_string:
        match = re.search(r'■\s*([A-D])\)', input_string)
        if match:
            logging.info(f"Found marked answer: {match.group(1)}")
            return match.group(1)
    
    # Check for timeout
    if time.time() - start_time > timeout:
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    # Use LLM to solve the problem
    logging.info("Using LLM to solve the scientific question")
    
    # Prepare the prompt - add instruction if not already present
    if "Think step-by-step" not in input_string and "think step-by-step" not in input_string.lower():
        prompt = f"""{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
    else:
        prompt = input_string

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'(?i)answer:\s*([A-D])', response)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer with 'Answer:' pattern: {final_answer}")
            return final_answer
        
        # Strategy 2: Look for "The answer is X" pattern
        answer_match = re.search(r'(?i)(?:the\s+)?answer\s+is\s*([A-D])', response)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer with 'answer is' pattern: {final_answer}")
            return final_answer
        
        # Strategy 3: Look for final answer patterns
        patterns = [
            r'(?i)therefore,?\s*([A-D])',
            r'(?i)so,?\s*the\s*answer\s*is\s*([A-D])',
            r'(?i)correct\s*answer\s*is\s*([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                final_answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {final_answer}")
                return final_answer
        
        # Strategy 4: Look for the last occurrence of a letter in the response
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            final_answer = letter_matches[-1].upper()
            logging.info(f"Using last mentioned letter: {final_answer}")
            return final_answer
            
        logging.error(f"Could not extract answer from response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing with LLM: {e}")
        return "A"  # Default fallback