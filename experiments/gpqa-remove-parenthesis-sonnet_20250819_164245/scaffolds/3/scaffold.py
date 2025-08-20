import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s limit
    
    try:
        question = input_string.strip()
        
        # Check timeout before first LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        logging.info("Sending question to LLM for step-by-step analysis")
        
        # Use the question as-is since it already includes the instruction format
        response = execute_llm(question)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer using multiple parsing strategies
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If parsing failed, try a more direct approach
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default after first attempt")
            return "A"
            
        logging.warning("Could not parse answer, trying direct question")
        
        direct_prompt = f"""Answer this multiple choice question with just the letter A, B, C, or D:

{question}

Answer:"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response}")
        
        simple_answer = extract_simple_answer(direct_response)
        if simple_answer:
            logging.info(f"Extracted from direct response: {simple_answer}")
            return simple_answer
        
        logging.error("All parsing attempts failed")
        return "A"  # Fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"

def extract_answer(response: str) -> str:
    """Extract answer using multiple parsing strategies."""
    
    # Strategy 1: Look for "Answer: <letter>" format (most likely)
    pattern1 = r"Answer:\s*([A-D])\b"
    match = re.search(pattern1, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 2: Look for "Answer: &lt;letter&gt;" (HTML encoded)
    pattern2 = r"Answer:\s*&lt;([A-D])&gt;"
    match = re.search(pattern2, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 3: Look for "the answer is X" patterns
    pattern3 = r"(?:the\s+)?answer\s+is\s+([A-D])\b"
    match = re.search(pattern3, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 4: Look at the end of response for standalone letters
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        line = line.strip()
        if re.match(r'^[A-D]$', line.upper()):
            return line.upper()
        
        # Look for letter followed by closing parenthesis at end of line
        match = re.search(r'\b([A-D])\)\s*$', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 5: Look for final letter in common answer formats
    final_patterns = [
        r'(?:^|\s)([A-D])(?:\)|\.|\s|$)',  # Letter with punctuation
        r'\b([A-D])\b(?=\s*$)',            # Letter at very end
    ]
    
    # Check last few sentences
    sentences = re.split(r'[.!?]\s+', response)
    for sentence in reversed(sentences[-2:]):
        for pattern in final_patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                return match.group(1).upper()
    
    return None

def extract_simple_answer(response: str) -> str:
    """Extract answer from a simple/direct response."""
    
    clean = response.strip().upper()
    
    # If it's just a single letter
    if clean in ['A', 'B', 'C', 'D']:
        return clean
    
    # Look for letter at start or after "Answer:"
    for pattern in [r'^([A-D])\b', r'Answer:\s*([A-D])\b']:
        match = re.search(pattern, clean)
        if match:
            return match.group(1)
    
    # Look for any valid letter
    for letter in ['A', 'B', 'C', 'D']:
        if letter in clean:
            return letter
    
    return None