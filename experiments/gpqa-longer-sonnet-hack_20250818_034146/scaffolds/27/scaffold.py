import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 100  # Conservative timeout to ensure completion
    
    try:
        logging.info("Starting to process scientific question")
        
        # Check for timeout early
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached early, returning default")
            return "A"
        
        # The input already contains the question and instruction format
        text = input_string.strip()
        
        # Create a focused prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across all scientific disciplines. Please solve this question carefully.

{text}

Important: End your response with exactly "Answer: X" where X is the correct letter."""

        response = execute_llm(prompt)
        logging.info(f"Got LLM response of length {len(response)}")
        
        # Extract the answer using the expected format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback extraction patterns
        fallback_patterns = [
            r'final answer.*?is\s*([ABCD])',
            r'answer.*?is\s*([ABCD])',
            r'correct.*?answer.*?([ABCD])',
            r'therefore.*?([ABCD])',
            r'conclusion.*?([ABCD])'
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Fallback pattern extracted answer: {answer}")
                return answer
        
        # Final fallback: look for single letters near the end of response
        end_section = response[-300:]  # Last 300 characters
        letters = re.findall(r'\b([ABCD])\b', end_section)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"End section extracted answer: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer from LLM response, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred during processing: {e}")
        return "A"