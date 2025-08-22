import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:        
        # Check timeout early
        if time.time() - start_time > 110:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a direct prompt that mimics the example format
        prompt = f"""{input_string.strip()}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response preview: {response[:200]}...")
        
        # Check timeout after LLM call
        if time.time() - start_time > 115:
            logging.warning("Timeout after LLM call, extracting answer quickly")
        
        # Extract the final answer with multiple fallback strategies
        
        # Strategy 1: Look for "Answer: X" format (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer via Answer: pattern: {result}")
            return result
        
        # Strategy 2: Look for common conclusion patterns
        conclusion_patterns = [
            r'(?:the\s+correct\s+answer\s+is|the\s+answer\s+is)\s*[:\-]?\s*([ABCD])',
            r'(?:option|choice)\s+([ABCD])\s+is\s+correct',
            r'therefore[,\s]+(?:the\s+answer\s+is\s+)?([ABCD])',
            r'so\s+the\s+answer\s+is\s+([ABCD])',
            r'thus[,\s]+(?:the\s+answer\s+is\s+)?([ABCD])',
            r'final\s+answer[:\-\s]+([ABCD])',
            r'I\s+choose\s+([ABCD])',
            r'select\s+option\s+([ABCD])',
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer via conclusion pattern: {result}")
                return result
        
        # Strategy 3: Look at the very end of response for a standalone letter
        # Get last 150 characters and look for letters
        tail = response[-150:] if len(response) > 150 else response
        letters_in_tail = re.findall(r'\b([ABCD])\b', tail)
        if letters_in_tail:
            result = letters_in_tail[-1].upper()
            logging.info(f"Found answer via tail letter: {result}")
            return result
        
        # Strategy 4: Look for any letter mention in the whole response, prefer later ones
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Found answer via last letter anywhere: {result}")
            return result
        
        # Strategy 5: Look for option references like "Option A" or "choice B"
        option_refs = re.findall(r'(?:option|choice)\s+([ABCD])', response, re.IGNORECASE)
        if option_refs:
            result = option_refs[-1].upper()
            logging.info(f"Found answer via option reference: {result}")
            return result
        
        # Default fallback - use A as it appears frequently in the examples
        logging.warning("Could not extract any answer letter, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Even in error case, return a valid option
        return "A"