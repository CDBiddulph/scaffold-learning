import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    question_text = input_string.strip()
    
    # Use LLM to solve the multiple choice question
    prompt = f"""{question_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)} chars")
        
        # Primary extraction: Look for "Answer: X" pattern
        match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Backup extraction methods if primary fails
        backup_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*([ABCD])',
            r'(?:choose|select|pick)\s*(?:option\s*)?([ABCD])',
            r'([ABCD])\s*(?:is\s+)?(?:correct|right|the\s+answer)',
            r'option\s*([ABCD])\s*(?:is|should|would)',
            r'\b([ABCD])\)\s*(?:is\s+correct|correct|right)'
        ]
        
        for i, pattern in enumerate(backup_patterns):
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer with backup pattern {i}: {answer}")
                return answer
        
        # Last resort: Look for isolated letters in the final lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            line = line.strip()
            # Single letter on a line
            if len(line) == 1 and line.upper() in ['A', 'B', 'C', 'D']:
                answer = line.upper()
                logging.info(f"Found isolated letter answer: {answer}")
                return answer
            # Letter with minimal context
            match = re.search(r'\b([ABCD])\b', line)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found letter in final lines: {answer}")
                return answer
        
        # If all extraction fails, log the response for debugging
        logging.error(f"Could not extract answer from response. First 300 chars: {response[:300]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe fallback