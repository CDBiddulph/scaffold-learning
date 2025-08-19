import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the question text and multiple choice options from the input."""
    # Clean up HTML entities
    text = input_string.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
    
    # Split by lines
    lines = text.strip().split('\n')
    
    # Find where the question starts (after the validation function)
    question_start = 0
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            question_start = i + 1
            break
    
    # Extract everything from after the validation function
    question_lines = []
    for i in range(question_start, len(lines)):
        line = lines[i].strip()
        if line:  # Skip empty lines
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines)
    return question_text

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question
        question_text = extract_question_and_options(input_string)
        
        logging.info(f"Extracted question, length: {len(question_text)}")
        
        # Check if we're running out of time
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The question already includes the instruction to think step-by-step and format the answer
        # So we can pass it directly to the LLM
        response = execute_llm(question_text)
        
        logging.info(f"LLM provided response")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with Answer: pattern: {answer}")
            return answer
        
        # Look for answer at the very end of response
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        # Check if the last line is just a single letter
        if lines and len(lines[-1]) == 1 and lines[-1].upper() in 'ABCD':
            answer = lines[-1].upper()
            logging.info(f"Found single letter answer at end: {answer}")
            return answer
        
        # Look for letters in the last few lines with various patterns
        for line in reversed(lines[-5:]):  # Check last 5 non-empty lines
            # Look for patterns like "A)", "(A)", "A.", "A:", etc.
            match = re.search(r'[:\(\.\s]([ABCD])[:\)\.\s]*$', line, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern in line '{line}': {answer}")
                return answer
        
        # Fallback: look for any occurrence of A, B, C, or D in the response
        # Prioritize occurrences in the later part of the response
        last_part = response[-1000:]  # Last 1000 characters
        letters = re.findall(r'\b([ABCD])\b', last_part, re.IGNORECASE)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Fallback answer from last part: {answer}")
            return answer
        
        # If still no clear answer found, return A as default
        logging.warning("No clear answer found in LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback