import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer from the 120s limit
    
    try:
        # Check if we're approaching timeout before making the call
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout before LLM call, returning default answer")
            return "A"
        
        logging.info("Processing scientific multiple choice question")
        
        # Pass the input directly to the LLM since it's already a complete prompt
        response = execute_llm(input_string)
        
        logging.info(f"LLM response length: {len(response)} characters")
        logging.info(f"LLM response preview: {response[:300]}...")
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached after LLM call, extracting answer quickly")
        
        # Extract the answer using multiple patterns, in order of preference
        extraction_patterns = [
            # Most specific patterns first
            r'Answer:\s*([A-D])\b',  # "Answer: A" format (expected format)
            r'Final Answer:\s*([A-D])\b',  # Alternative format
            r'answer.*?is\s*([A-D])\b',  # "answer is A"
            r'correct.*?answer.*?([A-D])\b',  # "correct answer A" or similar
            r'choose\s*([A-D])\b',  # "choose A"
            r'select\s*([A-D])\b',  # "select A"
            # More general patterns
            r'\b([A-D])\)\s*(?:is\s*)?correct',  # "A) is correct" or "A) correct"
            r'option\s*([A-D])',  # "option A"
            r'\b([A-D])\b(?=\s*$)',  # Letter at the end of a line
        ]
        
        for i, pattern in enumerate(extraction_patterns):
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer '{answer}' using pattern {i+1}")
                return answer
        
        # Fallback: look for isolated letters A-D in the response
        isolated_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if isolated_letters:
            # Prefer letters that appear near the end of the response
            answer = isolated_letters[-1].upper()
            logging.info(f"Fallback: using last isolated letter: {answer}")
            return answer
        
        # More aggressive fallback: any occurrence of A, B, C, or D
        any_letters = re.findall(r'([A-D])', response, re.IGNORECASE)
        if any_letters:
            answer = any_letters[-1].upper()
            logging.warning(f"Aggressive fallback: using any letter found: {answer}")
            return answer
        
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Full response was: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        elapsed = time.time() - start_time
        logging.error(f"Error occurred after {elapsed:.2f} seconds")
        return "A"  # Safe fallback

def validate_answer(answer: str) -> str:
    """Ensure the answer is a valid option"""
    if answer.upper() in ['A', 'B', 'C', 'D']:
        return answer.upper()
    else:
        logging.warning(f"Invalid answer '{answer}', defaulting to A")
        return "A"