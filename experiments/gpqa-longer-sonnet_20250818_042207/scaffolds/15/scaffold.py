import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_limit = 100  # Leave 20 second buffer from 120 second limit
    
    try:
        # Check timeout before starting
        if time.time() - start_time > timeout_limit:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering. You excel at solving complex technical problems through careful step-by-step analysis. When solving multiple choice questions, you methodically evaluate each option using scientific principles and select the most accurate answer."""
        
        logging.info("Processing scientific question with LLM")
        
        response = execute_llm(input_string, system_prompt)
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout_limit:
            logging.warning("Approaching timeout after LLM call")
        
        logging.info("Received LLM response, extracting answer")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" 
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using strategy 1: {result}")
            return result
        
        # Strategy 2: Look for "answer is X"
        answer_match = re.search(r'answer\s+is\s+([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using strategy 2: {result}")
            return result
        
        # Strategy 3: Look for "The correct answer is X"
        answer_match = re.search(r'correct\s+answer\s+is\s+([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using strategy 3: {result}")
            return result
        
        # Strategy 4: Look for "(X)" at the end
        answer_match = re.search(r'\(([ABCD])\)\s*$', response, re.MULTILINE | re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using strategy 4: {result}")
            return result
        
        # Strategy 5: Use the last letter mentioned
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Found answer using strategy 5 (last letter): {result}")
            return result
        
        logging.error("No answer found in response, defaulting to A")
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"