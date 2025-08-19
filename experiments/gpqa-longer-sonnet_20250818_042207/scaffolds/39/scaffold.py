import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 100  # Leave buffer before the 120s timeout
    
    logging.info("Processing multiple choice question")
    
    try:
        # Check timeout before starting
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout reached before processing")
            return "A"
        
        # The input already contains instructions for step-by-step thinking
        # Pass it directly to the LLM
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response received (first 300 chars): {response[:300]}...")
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout reached after LLM response")
            return "A"
        
        # Extract the final answer
        answer = extract_answer(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If extraction failed, try a more direct approach
        logging.warning("Could not extract clear answer, trying simplified prompt")
        
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout reached before retry")
            return "A"
        
        # Create a simpler, more direct prompt
        simplified_prompt = f"""Please answer this multiple choice question with just the letter A, B, C, or D:

{input_string.strip()}

Your answer:"""
        
        simple_response = execute_llm(simplified_prompt)
        logging.info(f"Simplified response: {simple_response[:100]}")
        
        # Extract answer from simplified response
        simple_answer = extract_answer(simple_response)
        
        if simple_answer and simple_answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Extracted answer from simplified approach: {simple_answer}")
            return simple_answer
        
        # Final fallback - just look for any letter in the simple response
        fallback_match = re.search(r'[ABCD]', simple_response.upper())
        if fallback_match:
            logging.info(f"Fallback extraction: {fallback_match.group()}")
            return fallback_match.group()
        
        # Ultimate fallback
        logging.warning("All extraction attempts failed, returning default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"

def extract_answer(response):
    """Extract the final answer from the LLM response using multiple strategies"""
    
    if not response:
        return None
    
    # Strategy 1: Look for "Answer: <letter>" patterns (handles HTML encoding)
    answer_patterns = [
        r'Answer:\s*(?:&lt;|<)?\s*([ABCD])\s*(?:&gt;|>)?',  # Answer: <A> or Answer: A
        r'Answer:\s*([ABCD])',  # Answer: A
        r'answer:\s*([ABCD])',  # answer: A (lowercase)
        r'Final\s+answer:\s*([ABCD])',  # Final answer: A
        r'The\s+answer\s+is\s*([ABCD])',  # The answer is A
        r'My\s+answer\s+is\s*([ABCD])',  # My answer is A
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 2: Look for letters in common formatting
    bracket_patterns = [
        r'\(([ABCD])\)',  # (A)
        r'\[([ABCD])\]',  # [A]
        r'^\s*([ABCD])\s*$',  # Just the letter on its own line
    ]
    
    for pattern in bracket_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
        if matches:
            return matches[-1].upper()  # Return the last match
    
    # Strategy 3: Look for standalone letters, but prefer those near the end
    letter_matches = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
    if letter_matches:
        # Return the last occurrence, as it's most likely the final answer
        return letter_matches[-1].upper()
    
    # Strategy 4: Look for any A, B, C, or D character (very permissive fallback)
    char_match = re.search(r'[ABCD]', response.upper())
    if char_match:
        return char_match.group()
    
    return None