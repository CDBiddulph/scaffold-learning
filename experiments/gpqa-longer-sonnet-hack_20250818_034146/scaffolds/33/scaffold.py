import logging
import re
from llm_executor import execute_llm
import time

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 110  # Leave buffer before timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check for timeout early
        if time.time() - start_time > max_time:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
        
        # Pass the input directly to the LLM since it already contains
        # good instructions for step-by-step reasoning and answer format
        response = execute_llm(input_string.strip())
        
        logging.info(f"Received LLM response (length: {len(response)})")
        
        # Parse the response to extract the answer letter
        # Strategy 1: Look for the requested "Answer: <letter>" format
        answer_pattern = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_pattern:
            answer = answer_pattern.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Strategy 2: Look for alternative answer patterns
        backup_patterns = [
            r'(?:the\s+)?answer\s+is\s*([A-D])',
            r'correct\s+(?:answer\s+)?is\s*([A-D])',
            r'final\s+answer\s*:?\s*([A-D])',
            r'therefore\s*,?\s*([A-D])',
        ]
        
        for pattern in backup_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using backup pattern: {answer}")
                return answer
        
        # Strategy 3: Look for standalone letter near the end of response
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        for line in reversed(lines[-10:]):  # Check last 10 non-empty lines
            if re.match(r'^[A-D]$', line):
                answer = line.upper()
                logging.info(f"Found standalone answer letter: {answer}")
                return answer
        
        # Strategy 4: Find the last occurrence of any option letter
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned option letter: {answer}")
            return answer
        
        # Default fallback if no answer found
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"  # Safe default