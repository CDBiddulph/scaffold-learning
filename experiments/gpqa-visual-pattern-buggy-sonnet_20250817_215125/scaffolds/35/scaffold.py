import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120s limit
    
    try:
        # Basic input validation
        if not input_string or not input_string.strip():
            logging.error("Empty input provided")
            return "A"
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        # Send the input directly to the LLM (it already contains proper instructions)
        response = execute_llm(input_string.strip())
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout after LLM call")
            return "A"
        
        if not response:
            logging.error("Empty response from LLM")
            return "A"
        
        logging.info(f"LLM response length: {len(response)} characters")
        logging.debug(f"LLM response preview: {response[:200]}...")
        
        # Extract the final answer - look for "Answer: <letter>" first (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {result}")
            return result
        
        # Try other common answer patterns
        patterns = [
            (r'final\s+answer\s*:?\s*([A-D])', "final answer pattern"),
            (r'(?:the\s+answer\s+is|choice\s+is|option\s+is)\s*:?\s*([A-D])', "answer is pattern"),
            (r'([A-D])\s*(?:is\s+correct|is\s+the\s+answer|is\s+the\s+correct\s+choice)', "correct answer pattern"),
            (r'(?:choose|select|pick)\s*:?\s*([A-D])', "choose pattern"),
        ]
        
        for pattern, description in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer using {description}: {result}")
                return result
        
        # Look for letters near the end of the response (likely the final answer)
        lines = response.strip().split('\n')
        for i, line in enumerate(reversed(lines[-5:])):  # Check last 5 lines
            letters = re.findall(r'\b([A-D])\b', line)
            if letters:
                result = letters[-1].upper()
                logging.info(f"Found answer in line {i+1} from end: {result}")
                return result
        
        # Final fallback: any letter A-D in the response (take the last one)
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Found answer using fallback (last letter): {result}")
            return result
        
        logging.warning("Could not extract any answer letter from response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"