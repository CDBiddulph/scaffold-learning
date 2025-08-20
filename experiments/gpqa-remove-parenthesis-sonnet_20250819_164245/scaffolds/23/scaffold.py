import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for processing
    
    try:
        # Clean up input - remove the instruction about format if present
        input_clean = re.sub(
            r'Think step-by-step.*?format.*?letter.*?["\'].*?\.?$', 
            '', 
            input_string, 
            flags=re.MULTILINE | re.DOTALL | re.IGNORECASE
        ).strip()
        
        # If that didn't work, try simpler pattern
        if input_clean == input_string.strip():
            input_clean = re.sub(
                r'Think step-by-step.*$', 
                '', 
                input_string, 
                flags=re.MULTILINE | re.DOTALL
            ).strip()
        
        # Construct comprehensive prompt for the LLM
        prompt = f"""{input_clean}

Please analyze this scientific question systematically:

1. Identify the key concepts and domain knowledge required
2. Work through the problem step by step
3. Evaluate each option carefully
4. Apply relevant scientific principles
5. Select the most appropriate answer

Provide your reasoning and then conclude with your final answer in the format "Answer: X" where X is A, B, C, or D."""

        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        logging.info(f"Received response of {len(response)} characters")
        
        # Primary extraction: look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {result}")
            return result
        
        # Fallback 1: "Answer X" without colon
        answer_match2 = re.search(r'Answer\s+([A-D])', response, re.IGNORECASE)
        if answer_match2:
            result = answer_match2.group(1).upper()
            logging.info(f"Extracted answer (fallback 1): {result}")
            return result
        
        # Fallback 2: Look for final letter in parentheses like "(A)"
        paren_match = re.findall(r'\(([A-D])\)', response)
        if paren_match:
            result = paren_match[-1].upper()
            logging.info(f"Extracted answer from parentheses: {result}")
            return result
        
        # Fallback 3: Last standalone A, B, C, or D in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using last standalone letter: {result}")
            return result
        
        # If we still haven't found an answer, try once more with a direct question
        if time.time() - start_time < timeout - 10:  # Leave time for second attempt
            logging.info("No clear answer found, making direct request")
            direct_prompt = f"""Based on this scientific question, which option (A, B, C, or D) is correct?

{input_clean}

Simply respond with the single letter of your choice: A, B, C, or D."""
            
            direct_response = execute_llm(direct_prompt)
            logging.info(f"Direct response: {direct_response}")
            
            # Extract single letter from direct response
            letter_match = re.search(r'\b([A-D])\b', direct_response)
            if letter_match:
                result = letter_match.group(1).upper()
                logging.info(f"Extracted from direct question: {result}")
                return result
        
        logging.warning("Could not extract answer from any method, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"