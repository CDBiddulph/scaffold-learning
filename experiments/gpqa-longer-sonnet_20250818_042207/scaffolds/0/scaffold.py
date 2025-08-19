import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Send the input directly to the LLM as it already contains the question,
        # choices, and instruction to think step-by-step
        response = execute_llm(input_string.strip())
        
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract the final answer - try multiple methods for robustness
        
        # Method 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            letter = answer_match.group(1).upper()
            logging.info(f"Found answer using Method 1: {letter}")
            return f"Answer: {letter}"
        
        # Method 2: Look for answer at the end of response
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        
        # Check last few lines for single letter
        for line in reversed(lines[-5:]):
            if re.match(r'^[A-D]$', line):
                logging.info(f"Found answer using Method 2: {line}")
                return f"Answer: {line}"
        
        # Method 3: Look for patterns like "The answer is A"
        for line in reversed(lines[-5:]):
            match = re.search(r'\b(?:answer|choice|option|correct)\s+(?:is\s+)?([A-D])\b', line, re.IGNORECASE)
            if match:
                letter = match.group(1).upper()
                logging.info(f"Found answer using Method 3: {letter}")
                return f"Answer: {letter}"
        
        # Method 4: Look for letter in parentheses at end
        if lines:
            last_line = lines[-1]
            match = re.search(r'\(([A-D])\)', last_line)
            if match:
                letter = match.group(1).upper()
                logging.info(f"Found answer using Method 4: {letter}")
                return f"Answer: {letter}"
        
        # Method 5: Look anywhere in the last paragraph for answer indicators
        last_paragraph = ' '.join(lines[-3:]) if len(lines) >= 3 else ' '.join(lines)
        match = re.search(r'\b([A-D])\s*(?:is\s+(?:the\s+)?(?:correct|right|answer))', last_paragraph, re.IGNORECASE)
        if match:
            letter = match.group(1).upper()
            logging.info(f"Found answer using Method 5: {letter}")
            return f"Answer: {letter}"
        
        logging.error("Could not extract answer from LLM response")
        logging.error(f"Last few lines of response: {lines[-3:] if len(lines) >= 3 else lines}")
        
        return "Error: Could not determine answer"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return f"Error: {str(e)}"