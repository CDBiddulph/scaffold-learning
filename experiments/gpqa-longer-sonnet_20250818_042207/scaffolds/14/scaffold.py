import logging
import time
import re
from llm_executor import execute_llm

def extract_answer_letter(response: str) -> str:
    """Extract the answer letter from LLM response with multiple fallback strategies"""
    
    # Strategy 1: Look for "Answer: X" pattern (most reliable)
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look in the last part of the response for answer patterns
    last_part = response[-1000:] if len(response) > 1000 else response
    
    patterns = [
        r'final answer[:\s]*([ABCD])',
        r'the answer is[:\s]*([ABCD])',  
        r'correct answer[:\s]*([ABCD])',
        r'my answer[:\s]*([ABCD])',
        r'\bAnswer[:\s]*([ABCD])\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, last_part, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look for standalone letter at end
    lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
    for line in reversed(lines[-10:]):  # Check last 10 non-empty lines
        # Exact match
        if line.upper() in ['A', 'B', 'C', 'D']:
            return line.upper()
        # Match "A)" or "A." or similar
        match = re.match(r'^([ABCD])[\)\.\s]*$', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 4: Look for letters in context
    context_match = re.search(r'\b(?:choose|select|answer|option)\s*([ABCD])\b', last_part, re.IGNORECASE)
    if context_match:
        return context_match.group(1).upper()
    
    # Strategy 5: Last resort - find any letter in the last 200 characters
    letter_mentions = re.findall(r'\b([ABCD])\b', response[-200:])
    if letter_mentions:
        return letter_mentions[-1].upper()
    
    # Default fallback
    logging.warning("Could not extract answer, using default 'A'")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing multiple choice question")
        
        # Check timeout before making the LLM call
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.error("Approaching timeout before LLM call")
            return "A"
        
        # The input already contains proper instructions, pass it directly
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        logging.info(f"Extracted answer: {answer}")
        
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer extracted: {answer}, defaulting to A")
            return "A"
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback