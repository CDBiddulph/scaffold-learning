import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_runtime = 115  # Leave some buffer before the 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check if we're approaching timeout
        if time.time() - start_time > max_runtime:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input contains a scientific question with multiple choice options
        # and instructions for step-by-step reasoning and answer format
        response = execute_llm(input_string)
        
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Primary method: look for "Answer: <letter>" pattern (case insensitive)
        answer_matches = re.findall(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_matches:
            final_answer = answer_matches[-1].upper()  # Take last match, ensure uppercase
            logging.info(f"Extracted answer from 'Answer:' pattern: {final_answer}")
            return final_answer
        
        # Fallback 1: look for "Answer <letter>" pattern (without colon)
        answer_matches = re.findall(r'Answer\s+([A-D])', response, re.IGNORECASE)
        if answer_matches:
            final_answer = answer_matches[-1].upper()
            logging.info(f"Extracted answer from 'Answer' pattern: {final_answer}")
            return final_answer
        
        # Fallback 2: look for lines containing only a single letter A-D
        lines = response.strip().split('\n')
        for line in reversed(lines):  # Start from the end
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone answer letter: {line}")
                return line
        
        # Fallback 3: look for "The answer is <letter>" pattern
        answer_matches = re.findall(r'(?:the\s+)?answer\s+is\s+([A-D])', response, re.IGNORECASE)
        if answer_matches:
            final_answer = answer_matches[-1].upper()
            logging.info(f"Found 'answer is' pattern: {final_answer}")
            return final_answer
        
        # Fallback 4: look for option format like A), B), C), D) at end of response
        option_matches = re.findall(r'\b([A-D])\)', response)
        if option_matches:
            final_answer = option_matches[-1].upper()
            logging.info(f"Found answer in option format: {final_answer}")
            return final_answer
        
        # Fallback 5: any standalone letter A-D near the end of the text
        # Split into words and look for single letters
        words = response.split()
        for word in reversed(words[-20:]):  # Check last 20 words
            word = word.strip('.,!?:;"()[]{}')
            if word in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer letter in final words: {word}")
                return word
        
        # If no clear answer found, log the issue and return default
        logging.error("Could not extract answer from response using any method")
        logging.error(f"Response preview: {response[:300]}...")
        return "A"  # Default to A if we can't determine the answer
        
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"  # Default fallback