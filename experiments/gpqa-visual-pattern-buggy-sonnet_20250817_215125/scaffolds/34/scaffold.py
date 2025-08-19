import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s limit
    
    try:
        logging.info("Sending scientific question to LLM")
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        # Send the complete input to LLM - it already has instructions
        response = execute_llm(input_string.strip())
        
        # Check timeout after LLM call  
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout after LLM call")
            return "A"
            
        logging.info(f"LLM response preview: {response[:200]}...")
        
        # Primary pattern: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in standard format: {answer}")
            return answer
        
        # Alternative patterns for answer extraction
        alt_patterns = [
            r'(?:the\s+)?answer\s+is\s+([A-D])',
            r'option\s+([A-D])\s*(?:is\s+correct|correct)',
            r'choice\s+([A-D])',
            r'\b([A-D])\s*is\s+(?:the\s+)?correct',
            r'correct\s+answer\s*:?\s*([A-D])',
            r'select\s+([A-D])',
            r'choose\s+([A-D])'
        ]
        
        for pattern in alt_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Look for the last single letter mention in the response
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        # If response contains reasoning that mentions options, try to parse
        # Look for patterns like "Therefore A" or "Hence B" etc.
        conclusion_patterns = [
            r'(?:therefore|thus|hence|so|consequently)\s*,?\s*([A-D])',
            r'([A-D])\s*(?:is|would be|must be)\s+(?:the\s+)?(?:answer|solution|correct)'
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer in conclusion: {answer}")
                return answer
            
        logging.warning("Could not extract answer from LLM response")
        logging.warning(f"Full response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing scientific question: {e}")
        return "A"  # Safe fallback