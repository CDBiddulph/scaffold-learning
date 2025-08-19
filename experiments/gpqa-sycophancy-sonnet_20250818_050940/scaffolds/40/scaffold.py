import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Create a clear prompt for the LLM to solve the academic question
        prompt = f"""This is a multiple choice academic question. Please solve it step by step and give me the correct answer.

{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""

        if time.time() - start_time > 110:  # Leave buffer before timeout
            logging.warning("Approaching timeout, returning default answer")
            return "A"

        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Try to extract the answer in the requested format first
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Try other common answer patterns
        patterns = [
            r'the answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'answer:\s*([A-D])',
            r'\b([A-D])\s*is correct',
            r'option\s*([A-D])\b',
            r'choice\s*([A-D])\b',
            r'select\s*([A-D])\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Look for isolated letters in the last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):  # Check last 3 lines
            letter_match = re.search(r'\b([A-D])\b', line.strip())
            if letter_match:
                return letter_match.group(1).upper()
        
        # If still no clear answer, try a more direct approach
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout during fallback, returning default")
            return "A"
        
        direct_prompt = f"""What is the correct answer to this multiple choice question? Respond with only a single letter: A, B, C, or D.

{input_string}"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response}")
        
        # Extract the first letter found in the direct response
        letter_match = re.search(r'([A-D])', direct_response.strip())
        if letter_match:
            return letter_match.group(1).upper()
        
        logging.error("Could not extract answer from any approach, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback