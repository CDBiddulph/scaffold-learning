import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Process a multiple choice scientific question and return the answer letter.
    """
    start_time = time.time()
    logging.info("Starting to process multiple choice question")
    
    # Mirror the format used in the examples exactly
    prompt = f"""{input_string.strip()}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

    try:
        # Check if we're running out of time (leave buffer for processing)
        if time.time() - start_time > 100:  # 100 seconds, leaving 20 second buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"Received response from LLM (length: {len(response)})")
        
        # Primary method: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-Z])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found explicit answer: {final_answer}")
            return final_answer
        
        # Secondary method: Look for conclusive statements in the last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):  # Check last 3 lines more carefully
            # Look for patterns like "the answer is X", "correct answer is X", etc.
            conclusion_patterns = [
                r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-Z])',
                r'(?:therefore|thus|hence).*?([A-Z])',
                r'(?:choose|select).*?([A-Z])',
                r'([A-Z])\s+is\s+(?:the\s+)?correct'
            ]
            
            for pattern in conclusion_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    final_answer = matches[-1].upper()
                    logging.info(f"Found answer via conclusion pattern: {final_answer}")
                    return final_answer
        
        # Tertiary method: Look for the last mentioned option letter in the format "X)"
        option_mentions = re.findall(r'\b([A-Z])\)', response)
        if option_mentions:
            # Get the last mentioned option, but validate it's likely a final choice
            final_answer = option_mentions[-1]
            logging.info(f"Using last mentioned option: {final_answer}")
            return final_answer
        
        # Quaternary method: Look for any single letter conclusions
        single_letter_conclusions = re.findall(r'\b([A-Z])\b', response.split('\n')[-1])
        if single_letter_conclusions:
            final_answer = single_letter_conclusions[-1]
            logging.info(f"Found single letter in final line: {final_answer}")
            return final_answer
        
        # Ultimate fallback
        logging.warning("Could not determine answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        # Return A as safe fallback
        return "A"