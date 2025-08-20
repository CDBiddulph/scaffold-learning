import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 20  # seconds to reserve
    
    try:
        logging.info("Starting to process multiple choice question")
        
        # The input already contains instructions for step-by-step reasoning
        # Pass it directly to the LLM
        response = execute_llm(input_string.strip())
        logging.info(f"Got LLM response of length {len(response)}")
        
        # Try to extract the answer letter
        answer = extract_answer_letter(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If parsing failed, try a more direct approach if we have time
        elapsed = time.time() - start_time
        if elapsed < (120 - timeout_buffer):
            logging.warning("Could not parse answer from first response, trying direct approach")
            
            # Create a simpler, more direct prompt
            direct_prompt = f"""{input_string.strip()}

Please respond with only the letter of your answer (A, B, C, or D)."""
            
            direct_response = execute_llm(direct_prompt)
            logging.info(f"Got direct response: {direct_response[:100]}")
            
            answer = extract_answer_letter(direct_response)
            if answer:
                logging.info(f"Direct approach worked: {answer}")
                return answer
        
        # Final fallback
        logging.error("Could not extract answer from any attempt")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"

def extract_answer_letter(text):
    """Extract answer letter using multiple strategies"""
    
    logging.info(f"Attempting to extract answer from text of length {len(text)}")
    
    # Primary strategy: Look for "Answer: X" pattern
    match = re.search(r'Answer:\s*([A-D])', text, re.IGNORECASE)
    if match:
        letter = match.group(1).upper()
        logging.info(f"Found answer with 'Answer:' pattern: {letter}")
        return letter
    
    # Secondary: "The answer is X"
    match = re.search(r'(?:the\s+)?answer\s+is\s+([A-D])', text, re.IGNORECASE)
    if match:
        letter = match.group(1).upper()
        logging.info(f"Found answer with 'answer is' pattern: {letter}")
        return letter
    
    # Look at the end of the text for standalone letters
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for i, line in enumerate(reversed(lines)):
        if len(line) == 1 and line.upper() in 'ABCD':
            letter = line.upper()
            logging.info(f"Found standalone letter at end: {letter}")
            return letter
        
        # Check for "A)" patterns
        match = re.match(r'^([A-D])\)?\s*$', line, re.IGNORECASE)
        if match:
            letter = match.group(1).upper()
            logging.info(f"Found letter with parenthesis pattern: {letter}")
            return letter
        
        # Don't look too far back
        if i > 5:
            break
    
    # Last resort: find all A-D letters and take the most recent
    letters = re.findall(r'\b([A-D])\b', text, re.IGNORECASE)
    if letters:
        letter = letters[-1].upper()
        logging.info(f"Found letter as last A-D in text: {letter}")
        return letter
    
    logging.warning("Could not extract any answer letter")
    return None