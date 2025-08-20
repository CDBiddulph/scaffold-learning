import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_from_response(response):
    """Extract the answer letter from LLM response using multiple methods."""
    
    # Method 1: Look for "Answer: <letter>" or "Answer: &lt;letter&gt;" patterns
    answer_patterns = [
        r'Answer:\s*([A-D])',
        r'Answer:\s*&lt;([A-D])&gt;',
        r'Answer:\s*<([A-D])>',
        r'final answer.*?([A-D])',
        r'answer is.*?([A-D])',
        r'the answer.*?([A-D])'
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer using pattern '{pattern}': {answer}")
            return answer
    
    # Method 2: Look for single letter at the end of response
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        line = line.strip()
        if len(line) == 1 and line.upper() in ['A', 'B', 'C', 'D']:
            answer = line.upper()
            logging.info(f"Found single letter answer at end: {answer}")
            return answer
    
    # Method 3: Look for letter followed by parenthesis (option format)
    option_matches = re.findall(r'\b([A-D])\)', response)
    if option_matches:
        answer = option_matches[-1].upper()  # Take last occurrence
        logging.info(f"Found option-style answer: {answer}")
        return answer
        
    # Method 4: Look for isolated letters in the final portion
    final_section = response[-200:]  # Last 200 characters
    isolated_letters = re.findall(r'\b([A-D])\b', final_section)
    if isolated_letters:
        answer = isolated_letters[-1].upper()
        logging.info(f"Found isolated letter in final section: {answer}")
        return answer
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Safety check for timeout (leave 5 second buffer)
        if time.time() - start_time > 115:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        question_text = input_string.strip()
        logging.info("Processing question")
        
        # Send question to LLM (questions already include formatting instructions)
        if time.time() - start_time > 110:
            logging.warning("Timeout approaching before LLM call")
            return "A"
            
        response = execute_llm(question_text)
        logging.info("Received LLM response")
        
        # Extract the answer
        answer = extract_answer_from_response(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract valid answer from response")
            # Log a portion of the response for debugging
            sample = response[-500:] if len(response) > 500 else response
            logging.warning(f"Response sample: {sample}")
            return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback on any error