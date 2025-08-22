import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check timeout early
        if time.time() - start_time > 100:  # Leave 20s buffer before timeout
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains the proper instruction format, so send it directly
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Strategy 1: Look for the exact requested format "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*<?\s*([ABCD])\s*>?', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using 'Answer:' format: {answer}")
            return answer
        
        # Strategy 2: Look for other explicit answer declarations
        answer_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*:?\s*([ABCD])',
            r'(?:therefore|thus|so)\s*,?\s*(?:the\s+answer\s+is\s*)?([ABCD])',
            r'final\s+answer\s*:?\s*([ABCD])',
            r'choose\s*(?:option\s*)?([ABCD])',
            r'select\s*(?:option\s*)?([ABCD])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look in the final lines for standalone letters or letters in context
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        if lines:
            # Check last few lines for patterns like "C is correct" or just "C"
            for line in reversed(lines[-5:]):
                # Standalone letter
                if re.match(r'^[ABCD]\.?$', line):
                    answer = line[0].upper()
                    logging.info(f"Found standalone answer: {answer}")
                    return answer
                
                # Letter with context indicating it's the answer
                context_match = re.search(r'([ABCD])\s+(?:is\s+)?(?:correct|right|the\s+answer)', line, re.IGNORECASE)
                if context_match:
                    answer = context_match.group(1).upper()
                    logging.info(f"Found contextual answer: {answer}")
                    return answer
        
        # Strategy 4: Find any letters mentioned, preferring later mentions
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        # If all else fails, default to A
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback