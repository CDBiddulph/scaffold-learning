import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second timeout
    
    try:
        # Use the input directly since it already contains good instructions
        response = execute_llm(input_string)
        logging.info(f"Response received, length: {len(response)}")
        
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout")
            return "A"
        
        # Primary method: look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' format: {answer}")
            return answer
        
        # Secondary: look for answer patterns in the last few lines
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        
        # Check last 5 lines for various patterns
        for line in reversed(lines[-5:]):
            patterns = [
                r'answer is ([A-D])',
                r'correct answer is ([A-D])',
                r'option ([A-D])',
                r'choice ([A-D])',
                r'([A-D])\s*is\s*correct',
                r'therefore[,\s]+([A-D])',
                r'so[,\s]+([A-D])',
                r'thus[,\s]+([A-D])',
                r'^([A-D])\)?\s*$'  # Just the letter
            ]
            
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    answer = match.group(1).upper()
                    logging.info(f"Found answer using pattern '{pattern}': {answer}")
                    return answer
        
        # Tertiary: look for any isolated letter A-D in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()  # Take the last one found
            logging.info(f"Fallback answer (last letter found): {answer}")
            return answer
        
        logging.error("No answer pattern found in response")
        logging.error(f"Last few lines: {lines[-3:] if len(lines) >= 3 else lines}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback