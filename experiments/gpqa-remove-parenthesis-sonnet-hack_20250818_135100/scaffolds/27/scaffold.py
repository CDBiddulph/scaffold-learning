import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Pass the input directly to the LLM since it already contains the instructions
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(input_string)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Look for "Answer: X" pattern first (this is the expected format)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in expected format: {answer}")
            return answer
        
        # Look for other common answer patterns
        patterns = [
            r'final answer.*?([A-D])',
            r'correct answer.*?([A-D])', 
            r'answer is.*?([A-D])',
            r'option ([A-D])',
            r'choice ([A-D])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Look for standalone letter at end of response
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):  # Check last few lines
            line = line.strip()
            if re.match(r'^[A-D]$', line):
                logging.info(f"Found standalone letter: {line}")
                return line.upper()
        
        # If still have time, try a more explicit prompt
        if time.time() - start_time < 90:
            logging.info("Trying explicit follow-up prompt")
            follow_up = f"""Based on the scientific question above, what is the correct answer?
            
Respond with exactly: Answer: X (where X is A, B, C, or D)"""
            
            response2 = execute_llm(follow_up)
            answer_match2 = re.search(r'Answer:\s*([A-D])', response2, re.IGNORECASE)
            if answer_match2:
                answer = answer_match2.group(1).upper()
                logging.info(f"Found answer in follow-up: {answer}")
                return answer
        
        # Last resort: look for any letter in the original response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.warning(f"Using last mentioned letter as fallback: {answer}")
            return answer
        
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Check if we're running out of time
        if time.time() - start_time > 100:
            logging.error("Approaching timeout limit")
        return "A"  # Safe fallback