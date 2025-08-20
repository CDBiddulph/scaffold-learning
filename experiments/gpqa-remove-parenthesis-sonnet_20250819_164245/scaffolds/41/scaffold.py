import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check for timeout to avoid getting minimum score
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # The input already contains the complete question and proper instructions
        # Pass it directly to the LLM
        response = execute_llm(input_string)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Strategy 1: Look for "Answer: X" format (what the instructions specifically ask for)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using Answer: format: {answer}")
            return answer
        
        # Strategy 2: Look for answer patterns in the last few lines
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        # Check last 5 lines for common answer patterns
        for i in range(min(5, len(lines))):
            line = lines[-(i+1)]
            
            answer_patterns = [
                r'(?:the\s+)?answer\s+is\s+([A-D])\b',
                r'therefore\s*,?\s*([A-D])\b', 
                r'thus\s*,?\s*([A-D])\b',
                r'hence\s*,?\s*([A-D])\b',
                r'so\s*,?\s*([A-D])\b',
                r'final\s+answer:\s*([A-D])\b',
                r'^([A-D])$'  # Single letter on its own line
            ]
            
            for pattern in answer_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    answer = match.group(1).upper()
                    logging.info(f"Found answer '{answer}' using pattern '{pattern}' in line: {line}")
                    return answer
        
        # Strategy 3: Find all valid option letters and use the last one mentioned
        # (assuming the LLM mentions the final answer last)
        valid_letters = re.findall(r'\b([A-D])\b', response)
        if valid_letters:
            answer = valid_letters[-1].upper()
            logging.info(f"Using last valid letter found: {answer}")
            return answer
        
        # Fallback if no answer found
        logging.warning("Could not extract answer from LLM response, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing scientific question: {e}")
        return "A"  # Safe fallback