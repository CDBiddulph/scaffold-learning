import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove the ■ symbol that marks correct answers in examples but preserve everything else
        cleaned_input = input_string.replace('■', '').strip()
        
        # Early timeout check
        if time.time() - start_time > 110:  # Leave buffer time
            logging.warning("Approaching time limit before LLM call")
            return "A"
        
        logging.info("Sending scientific question to LLM")
        response = execute_llm(cleaned_input)
        
        logging.info("Received LLM response, extracting answer")
        
        # Strategy 1: Look for explicit "Answer: X" format (highest confidence)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in Answer: format: {answer}")
            return answer
        
        # Strategy 2: Look for "the answer is X" variations (medium confidence)
        answer_is_patterns = [
            r'the answer is\s*([A-D])',
            r'answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'final answer is\s*([A-D])'
        ]
        
        for pattern in answer_is_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for letters in option format like "(C)" or "C)" (medium confidence)
        option_patterns = [
            r'\(([A-D])\)',  # (A)
            r'([A-D])\)',    # A)
            r'option\s*([A-D])'  # option A
        ]
        
        for pattern in option_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer in option format: {answer}")
                return answer
        
        # Strategy 4: Find all standalone A-D letters and take the last one (lowest confidence)
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer as standalone letter (last occurrence): {answer}")
            return answer
        
        # If nothing found, log the issue and return default
        logging.warning("Could not extract any answer from LLM response")
        logging.warning(f"Response preview: {response[:300]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing scientific question: {e}")
        return "A"  # Safe default fallback