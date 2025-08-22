import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Clean up the input
        text = input_string.strip()
        
        # Create a focused prompt for the LLM
        prompt = f"""You are a scientific expert. Please analyze this multiple choice question carefully and select the correct answer.

{text}

Think step-by-step through the scientific concepts involved, then provide your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""

        # Check timeout before LLM call
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:200]}...")
        
        # Extract the answer using multiple patterns
        extraction_patterns = [
            r'Answer:\s*([A-D])',           # "Answer: A"
            r'answer is\s*([A-D])',        # "answer is B"  
            r'correct answer is\s*([A-D])', # "correct answer is C"
            r'final answer.*?([A-D])',     # "final answer... D"
            r'I (?:choose|select)\s*([A-D])', # "I choose A"
            r'option\s*([A-D])',           # "option B"
            r'choice\s*([A-D])',           # "choice C"
        ]
        
        for pattern in extraction_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Extracted answer: {result}")
                return result
        
        # Last resort: find all letter mentions and use the last one
        # This handles cases where the LLM concludes with something like "Therefore, D"
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using last mentioned letter: {result}")
            return result
        
        # Absolute fallback
        logging.warning(f"Could not extract answer from response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"