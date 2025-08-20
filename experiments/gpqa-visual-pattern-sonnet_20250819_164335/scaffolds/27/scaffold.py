import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for safety
    
    try:
        # Clean up the input - remove instruction text if present
        text = input_string.strip()
        if "Think step-by-step" in text:
            text = text.split("Think step-by-step")[0].strip()
        
        logging.info(f"Processing question of length: {len(text)}")
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached before LLM call")
            return "A"
        
        # Create prompt for LLM to solve the question
        prompt = f"""You are an expert scientist with deep knowledge across multiple fields including physics, chemistry, biology, astronomy, mathematics, and engineering. 

Please solve this multiple choice question step by step:

{text}

Analyze the problem carefully, show your reasoning, and then provide your final answer in the exact format "Answer: X" where X is the letter of the correct choice (A, B, C, or D)."""
        
        # Get LLM response
        response = execute_llm(prompt)
        
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter using multiple patterns
        answer = extract_answer_letter(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Extracted answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not extract valid answer. Response snippet: {response[-200:]}")
            return "A"  # Default fallback
            
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"  # Safe fallback

def extract_answer_letter(response):
    """Extract the final answer letter from LLM response using multiple strategies"""
    
    # Strategy 1: Look for "Answer: X" pattern (most reliable)
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for common final answer phrases
    final_patterns = [
        r'final answer is\s*([ABCD])',
        r'correct answer is\s*([ABCD])',
        r'the answer is\s*([ABCD])',
        r'therefore,?\s*([ABCD])',
        r'so,?\s*([ABCD])',
        r'thus,?\s*([ABCD])',
        r'answer:\s*([ABCD])',
        r'choice\s*([ABCD])',
        r'option\s*([ABCD])'
    ]
    
    for pattern in final_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look for letters in parentheses or after conclusion words
    conclusion_patterns = [
        r'conclude\s*(?:that\s*)?(?:the\s*answer\s*is\s*)?([ABCD])',
        r'select\s*(?:option\s*)?([ABCD])',
        r'choose\s*(?:option\s*)?([ABCD])',
        r'\(([ABCD])\)(?:\s*(?:is|would|should)\s*(?:be\s*)?(?:the\s*)?(?:correct|right|answer))?'
    ]
    
    for pattern in conclusion_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()  # Take the last occurrence
    
    # Strategy 4: Find the last standalone letter mention
    # Look for letters that appear to be answers (not part of formulas/equations)
    lines = response.split('\n')
    for line in reversed(lines):  # Check from end backwards
        line = line.strip()
        if line and not re.search(r'[=+\-*/\d]', line):  # Skip lines with math
            letter_match = re.search(r'\b([ABCD])\b', line)
            if letter_match:
                return letter_match.group(1).upper()
    
    # Strategy 5: Last resort - find any occurrence of A, B, C, or D
    letters = re.findall(r'\b([ABCD])\b', response)
    if letters:
        return letters[-1].upper()
    
    return None