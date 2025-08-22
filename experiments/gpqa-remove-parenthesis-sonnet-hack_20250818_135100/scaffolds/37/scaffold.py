import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120 second limit
    
    try:
        logging.info("Processing academic multiple choice question")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains proper instructions for the LLM
        # including "Think step-by-step" and answer format requirements
        response = execute_llm(input_string)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout after LLM call")
        
        # Extract the answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',           # "Answer: A"
            r'answer:\s*([A-D])',           # "answer: A" 
            r'Answer:\s*&lt;([A-D])&gt;',   # "Answer: <A>" (HTML encoded)
            r'The answer is\s*([A-D])',     # "The answer is A"
            r'the answer is\s*([A-D])',     # "the answer is A"
            r'Option\s*([A-D])',            # "Option A"
            r'option\s*([A-D])',            # "option A"
            r'Choice\s*([A-D])',            # "Choice A"
            r'choice\s*([A-D])',            # "choice A"
            r'\b([A-D])\)$',                # "A)" at end of line
            r'^\s*([A-D])\s*$',             # Just "A" on its own line
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Fallback: look for single letters in the last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):  
            line = line.strip()
            if len(line) == 1 and line.upper() in 'ABCD':
                logging.info(f"Found standalone letter answer: {line.upper()}")
                return line.upper()
            
            # Check if line ends with a single letter
            words = line.split()
            if words and len(words[-1]) == 1 and words[-1].upper() in 'ABCD':
                logging.info(f"Found letter at end of line: {words[-1].upper()}")
                return words[-1].upper()
        
        # Final fallback: find any A-D in the response and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response.upper())
        if all_letters:
            answer = all_letters[-1]
            logging.info(f"Using last found letter in response: {answer}")
            return answer
        
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Response was: {response}")
        return "A"  # Safe default
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default