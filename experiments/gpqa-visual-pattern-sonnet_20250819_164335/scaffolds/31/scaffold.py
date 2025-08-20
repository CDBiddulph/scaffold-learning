import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info(f"Processing input of length {len(input_string)}")
        
        # The input already contains the complete question and instructions for step-by-step reasoning
        response = execute_llm(input_string)
        logging.info(f"LLM response: {response}")
        
        # Primary extraction: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer: {answer}")
            return answer
        
        # Fallback 1: Look for "The answer is X" or similar phrases
        answer_patterns = [
            r'(?:the\s+answer\s+is|answer\s+is)\s*([A-D])',
            r'(?:correct\s+answer\s+is|right\s+answer\s+is)\s*([A-D])',
            r'(?:choose|select)\s*([A-D])',
            r'(?:option|choice)\s*([A-D])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Fallback 2: Look for the last clear letter option mentioned
        # Find all isolated A, B, C, D letters (not part of longer words)
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer (last letter): {answer}")
            return answer
        
        # Fallback 3: Look for option references like "A)", "B)", etc.
        option_refs = re.findall(r'([A-D])\)', response)
        if option_refs:
            answer = option_refs[-1].upper()
            logging.info(f"Found answer (option reference): {answer}")
            return answer
            
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback