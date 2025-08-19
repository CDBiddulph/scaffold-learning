import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer before 120s timeout
    
    try:
        # Check for early timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout approaching at start")
            return "A"
        
        # Parse input to separate question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where multiple choice options start
        options_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^[A-D]\)', line):
                options_start = i
                break
        
        if options_start == -1:
            logging.error("Could not find multiple choice options A) B) C) D)")
            return "A"
        
        # Split question and options
        question_lines = lines[:options_start]
        option_lines = lines[options_start:]
        
        question = '\n'.join(question_lines)
        options = '\n'.join(option_lines)
        
        # Validate we have exactly 4 options
        option_count = len([line for line in option_lines if re.match(r'^[A-D]\)', line)])
        if option_count != 4:
            logging.warning(f"Expected 4 options A-D, found {option_count}")
        
        # Construct the complete problem
        full_problem = f"{question}\n\n{options}"
        
        # Create detailed prompt for step-by-step analysis
        prompt = f"""Analyze this multiple choice question carefully. Use your knowledge to work through the problem step-by-step, showing your reasoning clearly.

{full_problem}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
        
        # Check timeout before expensive LLM call
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout approaching before LLM call")
            return "A"
        
        # Get LLM analysis
        logging.info("Requesting step-by-step analysis from LLM")
        response = execute_llm(prompt)
        logging.info(f"LLM response received ({len(response)} chars)")
        
        # Extract the final answer letter
        # First try to find "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from pattern: {final_answer}")
            return final_answer
        
        # Backup approach: find the last letter A-D mentioned
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            final_answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {final_answer}")
            return final_answer
        
        # Final fallback if no clear answer found
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe fallback