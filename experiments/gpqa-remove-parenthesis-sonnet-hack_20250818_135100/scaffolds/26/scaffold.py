import re
import logging
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 120  # Given timeout is 120 seconds
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use the LLM to analyze the scientific question
        # The input already includes instructions to think step-by-step and format the answer
        prompt = f"""You are a scientific expert. Please analyze this multiple choice question carefully and provide the correct answer.

{input_string}"""

        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)} characters")
        
        # Try to extract the answer letter from the response
        # Look for the specific format: "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback patterns to catch other answer formats
        patterns = [
            r'The answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'option\s*([A-D])',
            r'choose\s*([A-D])',
            r'select\s*([A-D])',
            r'\b([A-D])\)(?=\s|$)',  # Letter followed by closing parenthesis
            r'^\s*([A-D])\b',  # Letter at start of line
            r'\b([A-D])\b(?=\s*$)',  # Single letter at end of response
            r'\b([A-D])\b'  # Any single letter as last resort
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using fallback pattern {i}: {answer}")
                return answer
        
        # If we absolutely can't extract any letter, return A as default
        logging.warning(f"Could not extract any answer letter from response: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"