import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Check for early timeout
        if time.time() - start_time > timeout:
            return "A"
            
        logging.info("Processing scientific problem")
        
        # Create a comprehensive prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across all scientific disciplines including chemistry, physics, astronomy, biology, mathematics, and engineering.

Please solve this scientific problem step by step:

{input_string.strip()}

Work through this systematically:
1. Identify the type of problem and relevant scientific principles
2. Break down the problem into logical steps  
3. Apply calculations or reasoning as needed
4. Compare your result with the given options
5. Select the correct answer

Please think through your reasoning carefully and end your response with "Answer: X" where X is the correct letter (A, B, C, or D)."""

        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call")
            return "A"
            
        logging.info("Sending problem to LLM for analysis")
        response = execute_llm(prompt)
        
        # Check timeout after LLM call  
        if time.time() - start_time > timeout:
            logging.warning("Timeout exceeded after LLM response")
            return "A"
            
        # Extract the answer from the response
        logging.info("Parsing LLM response for answer")
        
        # Look for "Answer: X" pattern (most explicit)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found explicit answer format: {result}")
            return result
            
        # Try other common answer patterns
        patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'(?:option|choice)\s+([A-D])',
            r'([A-D])\s+is\s+(?:the\s+)?(?:correct|right)',
            r'select\s+([A-D])',
            r'choose\s+([A-D])',
            r'\b([A-D])\)(?:\s|$)'  # Match letter followed by closing paren
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                result = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer using pattern {i}: {result}")
                return result
        
        # Fallback: look for any standalone letters A-D
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using last standalone letter found: {result}")
            return result
            
        # Ultimate fallback
        logging.warning("Could not parse answer from response, defaulting to A")
        logging.info(f"LLM response was: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return "A"