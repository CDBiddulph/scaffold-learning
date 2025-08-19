import logging
import re
import time
from llm_executor import execute_llm

def clean_input(input_string: str) -> str:
    """Remove the validation function and return the clean question."""
    lines = input_string.split('\n')
    
    # Find where the validation function ends
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            # Return everything after this line, cleaned up
            remaining_lines = lines[i+1:]
            # Remove empty lines from the start
            while remaining_lines and not remaining_lines[0].strip():
                remaining_lines = remaining_lines[1:]
            return '\n'.join(remaining_lines)
    
    # Fallback: return original if pattern not found
    return input_string

def extract_answer(response: str) -> str:
    """Extract the answer letter from LLM response."""
    # Look for "Answer: X" pattern (case insensitive)
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for the letter at the end of response
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    for line in reversed(lines):
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    # Look for other patterns like "The answer is A" or "(A)"
    answer_patterns = [
        r'answer is ([A-D])',
        r'correct answer is ([A-D])',
        r'\(([A-D])\)',
        r'option ([A-D])',
        r'choice ([A-D])'
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    logging.warning("Could not extract answer from response, defaulting to A")
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Clean the input by removing validation function
        clean_question = clean_input(input_string)
        logging.info(f"Cleaned input length: {len(clean_question)} characters")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Send to LLM - the input already has the right format after cleaning
        response = execute_llm(clean_question)
        logging.info("Received LLM response")
        
        # Extract the answer letter
        answer = extract_answer(response)
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback