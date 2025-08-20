import logging
import re
import html
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 100  # Leave buffer before 120s limit
    
    try:
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Decode HTML entities that might be in the input
        input_string = html.unescape(input_string)
        
        system_prompt = """You are an expert in multiple scientific disciplines including chemistry, physics, biology, astronomy, and mathematics. You will be presented with academic multiple-choice questions. Please analyze each question carefully and provide the best answer."""
        
        # Check if the input already includes the instruction to format the answer
        if "Think step-by-step" in input_string:
            # It already has the instruction, use as-is
            user_prompt = input_string.strip()
        else:
            # Add the instruction
            user_prompt = f"""{input_string.strip()}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""
        
        logging.info(f"Sending prompt to LLM")
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call, returning default answer")
            return "A"
        
        # Get response from LLM
        response = execute_llm(user_prompt, system_prompt)
        logging.info(f"LLM response received")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {result}")
            return result
        
        # Alternative patterns
        patterns = [
            r'(?:the\s+answer\s+is|final\s+answer\s+is):?\s*([A-D])',
            r'(?:choose|select|pick)\s+([A-D])',
            r'option\s+([A-D])',
            r'\b([A-D])\s*is\s+correct',
            r'\b([A-D])\s*is\s+the\s+answer'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {result}")
                return result
        
        # Look for the last occurrence of A, B, C, or D in isolation
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using last letter found: {result}")
            return result
        
        # If all else fails, return A as a default
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback