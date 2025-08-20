import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove training artifacts like ■ symbol
        cleaned_input = re.sub(r'■\s*', '', input_string)
        
        # Check if we're running out of time
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Use a focused prompt for the LLM
        prompt = f"""{cleaned_input}

Please analyze this question carefully and provide your reasoning step by step. Then give your final answer in the exact format "Answer: X" where X is the letter (A, B, C, or D) of the correct choice."""

        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer using multiple patterns
        patterns = [
            r'Answer:\s*([A-D])',  # Primary format
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*([A-D])',
            r'(?:option\s+)?([A-D])\s+is\s+(?:the\s+)?correct',
            r'I\s+(?:choose|select)\s+([A-D])',
            r'final\s+answer.*?([A-D])',
            r'\b([A-D])\b(?=\s*$)',  # Letter at end of response
        ]
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, response, re.IGNORECASE))
            if matches:
                answer = matches[-1].group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Fallback: find all A-D letters and use the last one mentioned
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last letter mentioned as fallback: {answer}")
            return answer
        
        logging.error("Could not extract any answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"