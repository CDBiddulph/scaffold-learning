import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Conservative timeout to avoid exceeding 120s limit
    
    try:
        logging.info("Processing academic multiple choice question")
        
        # Check for timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Create a focused prompt for the LLM
        prompt = f"""You are an expert academic problem solver. Solve this multiple choice question step-by-step:

{input_string.strip()}

Please:
1. Identify the subject area and type of problem
2. Extract the key information and determine what's being asked
3. Apply relevant scientific principles, formulas, or concepts
4. Work through calculations or logical reasoning systematically
5. Evaluate the answer choices and select the best one
6. End with "Answer: X" where X is your chosen letter

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            return "A"
            
        logging.info("Sending problem to LLM")
        response = execute_llm(prompt)
        
        # Check timeout after LLM response
        if time.time() - start_time > timeout:
            return "A"
            
        logging.info(f"Received LLM response ({len(response)} chars)")
        
        # Primary extraction method: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {result}")
            return result
        
        # Secondary extraction methods
        backup_patterns = [
            r'final answer is\s*([A-D])',
            r'the answer is\s*([A-D])', 
            r'correct answer is\s*([A-D])',
            r'therefore,?\s*([A-D])',
            r'so,?\s*the answer is\s*([A-D])',
            r'option\s*([A-D])\s*is correct',
            r'choose\s*([A-D])',
            r'select\s*([A-D])',
        ]
        
        for pattern in backup_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                result = matches[-1].upper()
                logging.info(f"Extracted answer using backup pattern: {result}")
                return result
        
        # Tertiary method: Look for letters with specific markers
        marker_patterns = [
            r'([A-D])\)\s*[^A-Za-z]*$',  # Letter followed by ) at end of line
            r'■\s*([A-D])',  # Letter with filled bullet (marked correct answer)
        ]
        
        for pattern in marker_patterns:
            matches = re.findall(pattern, response, re.MULTILINE)
            if matches:
                result = matches[-1].upper()
                logging.info(f"Extracted answer using marker pattern: {result}")
                return result
        
        # Last resort: Find the most recently mentioned answer choice
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {result}")
            return result
            
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"