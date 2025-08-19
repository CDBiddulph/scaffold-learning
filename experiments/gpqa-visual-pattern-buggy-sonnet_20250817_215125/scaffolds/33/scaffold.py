import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before the 120 second timeout
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Send the input directly to the LLM since it already contains the instruction format
        response = execute_llm(input_string)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the final answer from the response
        # Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' format: {answer}")
            return answer
        
        # Look for other explicit answer patterns
        final_patterns = [
            r'final answer is\s*([ABCD])',
            r'answer is\s*([ABCD])',
            r'choose\s*([ABCD])',
            r'select\s*([ABCD])',
            r'option\s*([ABCD])',
            r'the correct answer is\s*([ABCD])',
            r'therefore[,\s]*([ABCD])',
            r'thus[,\s]*([ABCD])',
            r'so[,\s]*([ABCD])'
        ]
        
        for pattern in final_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer from pattern '{pattern}': {answer}")
                return answer
        
        # If no explicit answer format found, look for final letter at the end of lines
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            # Look for lines that end with just a single letter
            if re.match(r'^[ABCD]$', line):
                logging.info(f"Found final answer at end of line: {line}")
                return line
        
        # Look for single letters A-D in the last few lines (likely conclusion)
        last_lines = '\n'.join(lines[-5:])  # Check last 5 lines
        single_letters = re.findall(r'\b([ABCD])\b', last_lines)
        if single_letters:
            answer = single_letters[-1]  # Take the last one
            logging.info(f"Using last found letter in final lines: {answer}")
            return answer
        
        # As a last resort, look for any A-D in the entire response
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1]  # Take the last one
            logging.warning(f"Using last found letter in entire response: {answer}")
            return answer
            
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Response was: {response[:500]}...")  # Log first 500 chars for debugging
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback