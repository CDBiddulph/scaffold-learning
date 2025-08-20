import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for processing
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check for timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached, returning default answer")
            return "A"
        
        # Craft a detailed prompt for the LLM
        system_prompt = """You are a world-class scientific expert with deep knowledge across all fields including biology, chemistry, physics, astronomy, quantum mechanics, materials science, and more. You excel at analyzing complex scientific problems and multiple choice questions."""
        
        prompt = f"""Analyze this scientific question carefully and determine the correct answer.

{input_string}

Think step-by-step through the scientific concepts involved:
1. Identify the key scientific principles and concepts
2. Analyze each answer choice systematically
3. Apply your scientific knowledge to eliminate incorrect choices
4. Determine which choice is scientifically correct

Provide your reasoning, then end your response with exactly: "Answer: <letter>" where <letter> is A, B, C, or D."""
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"Received LLM response, extracting answer...")
        
        # Extract the answer letter - try multiple patterns
        # Pattern 1: "Answer: X" 
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Pattern 2: "Answer <letter>" without colon
        answer_match = re.search(r'Answer\s+([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer (no colon): {answer}")
            return answer
        
        # Pattern 3: Look for letter at end of response
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):  # Check last 3 lines
            line = line.strip()
            if re.match(r'^[A-D]$', line):
                answer = line.upper()
                logging.info(f"Extracted answer from line: {answer}")
                return answer
        
        # Pattern 4: Look for any isolated letter A, B, C, or D
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()  # Take the last occurrence
            logging.info(f"Final fallback answer: {answer}")
            return answer
        
        # If nothing found, return A as default
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback