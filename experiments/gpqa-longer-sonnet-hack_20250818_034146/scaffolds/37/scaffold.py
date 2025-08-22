import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for the 120 second limit
    
    try:
        logging.info("Processing multiple choice question")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # The input already contains instructions for step-by-step reasoning
        # Pass directly to LLM for analysis
        response = execute_llm(input_string)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Try multiple extraction patterns in order of reliability
        
        # Pattern 1: "Answer: <letter>"
        match1 = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if match1:
            answer = match1.group(1).upper()
            logging.info(f"Found answer with standard format: {answer}")
            return answer
        
        # Pattern 2: "Answer: &lt;letter&gt;" (HTML encoded)
        match2 = re.search(r'Answer:\s*&lt;([ABCD])&gt;', response, re.IGNORECASE)
        if match2:
            answer = match2.group(1).upper()
            logging.info(f"Found HTML encoded answer: {answer}")
            return answer
        
        # Pattern 3: Letter at end of response
        match3 = re.search(r'\b([ABCD])\s*$', response.strip(), re.IGNORECASE)
        if match3:
            answer = match3.group(1).upper()
            logging.info(f"Found answer at end: {answer}")
            return answer
        
        # Pattern 4: Last letter with word boundaries (most reliable fallback)
        letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer from context (last of {len(letters)}): {answer}")
            return answer
        
        # Pattern 5: Any letter as absolute fallback
        any_match = re.search(r'([ABCD])', response, re.IGNORECASE)
        if any_match:
            answer = any_match.group(1).upper()
            logging.info(f"Found answer with fallback: {answer}")
            return answer
        
        # Ultimate fallback
        logging.error(f"Could not extract answer from: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"