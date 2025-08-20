import logging
import re
import time
from llm_executor import execute_llm

def clean_input(input_string):
    """Remove the validation function from the input."""
    lines = input_string.strip().split('\n')
    
    # Remove the validate_answer function lines
    clean_lines = []
    skip_function = False
    for line in lines:
        if 'def validate_answer' in line:
            skip_function = True
            continue
        if skip_function and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            skip_function = False
        if not skip_function:
            clean_lines.append(line)
    
    return '\n'.join(clean_lines).strip()

def extract_answer_from_response(response):
    """Extract the answer letter from the LLM response."""
    # First try to find "Answer: <letter>" format
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Try to find the pattern "Answer is <letter>" or similar
    answer_is_match = re.search(r'answer\s+is\s+([A-D])', response, re.IGNORECASE)
    if answer_is_match:
        return answer_is_match.group(1).upper()
    
    # Look for final answer at the end of the response
    lines = response.strip().split('\n')
    for line in reversed(lines[-10:]):  # Check last 10 lines
        # Look for standalone letters at the end of lines
        line_match = re.search(r'\b([A-D])\s*$', line.strip())
        if line_match:
            return line_match.group(1).upper()
    
    # Look for letters mentioned in the last few lines
    for line in reversed(lines[-5:]):
        letters = re.findall(r'\b([A-D])\b', line)
        if letters:
            return letters[-1].upper()
    
    # If nothing found, default to A
    logging.warning("Could not extract answer from response, defaulting to A")
    return "A"

def solve_question(question_text, max_time=100):
    """Use LLM to solve the question and return the letter answer."""
    start_time = time.time()
    
    try:
        # Check timeout before making LLM call
        if time.time() - start_time > max_time:
            logging.warning("Approaching timeout before LLM call, returning default answer")
            return "A"
            
        # Make the LLM call
        response = execute_llm(question_text)
        logging.info(f"LLM response length: {len(response)} characters")
        logging.info(f"LLM response preview: {response[:500]}...")
        
        # Extract the answer
        answer = extract_answer_from_response(response)
        return answer
        
    except Exception as e:
        logging.error(f"Error in solve_question: {e}")
        return "A"

def process_input(input_string: str) -> str:
    """Process the input and return the answer letter."""
    start_time = time.time()
    
    try:
        # Clean the input to remove validation function
        clean_question = clean_input(input_string)
        logging.info(f"Cleaned question preview: {clean_question[:300]}...")
        
        # Check if we have enough time left
        remaining_time = 110 - (time.time() - start_time)  # Leave 10 second buffer
        if remaining_time < 10:
            logging.warning("Not enough time remaining, returning default answer")
            return "A"
        
        # Solve the question
        answer = solve_question(clean_question, max_time=remaining_time)
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"