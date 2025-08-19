import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check if we're approaching the timeout (120 seconds)
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains the instruction to think step-by-step
        # and provide the answer in the format "Answer: <letter>"
        response = execute_llm(input_string)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Look for the pattern "Answer: <letter>" in the response (case insensitive)
        answer_pattern = r"Answer:\s*<?([A-D])>?"
        match = re.search(answer_pattern, response, re.IGNORECASE)
        
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer pattern: {answer}")
            return answer
        
        # If no exact match, look for other common answer patterns
        answer_patterns = [
            r"the answer is\s*<?([A-D])>?",
            r"correct answer is\s*<?([A-D])>?",
            r"answer:\s*<?([A-D])>?",
            r"final answer:\s*<?([A-D])>?",
            r"therefore,?\s*<?([A-D])>?",
            r"thus,?\s*<?([A-D])>?",
            r"choice\s*<?([A-D])>?",
            r"option\s*<?([A-D])>?"
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Look for a letter that appears at the end of the response
        # This catches cases where the LLM just states the letter
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if len(line) == 1 and line.upper() in ['A', 'B', 'C', 'D']:
                answer = line.upper()
                logging.info(f"Found single letter at end: {answer}")
                return answer
        
        # If still no match, look for any letter in the response and take the last one
        letter_pattern = r"\b([A-D])\b"
        matches = re.findall(letter_pattern, response, re.IGNORECASE)
        if matches:
            answer = matches[-1].upper()  # Return the last letter found
            logging.info(f"Found letter in text: {answer}")
            return answer
        
        # If still no match, log the response for debugging and return a default
        logging.error(f"Could not extract answer from response: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback