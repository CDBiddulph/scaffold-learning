import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check for timeout buffer (leave 10 seconds buffer)
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response: {response[:500]}...")  # Log first 500 chars
        
        # Extract the answer using multiple strategies
        answer = extract_answer_letter(response)
        logging.info(f"Extracted answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_answer_letter(response: str) -> str:
    """Extract the answer letter from LLM response using multiple strategies"""
    
    # Strategy 1: Look for explicit "Answer: X" patterns (most common format)
    answer_patterns = [
        r'Answer:\s*([ABCD])',
        r'answer:\s*([ABCD])', 
        r'Answer:\s*&lt;([ABCD])&gt;',
        r'answer:\s*&lt;([ABCD])&gt;',
        r'ANSWER:\s*([ABCD])',
        r'Answer:\s*\(([ABCD])\)',
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 2: Look for other common conclusion formats
    conclusion_patterns = [
        r'final answer.*?([ABCD])',
        r'I choose.*?([ABCD])',
        r'I select.*?([ABCD])',
        r'correct answer.*?([ABCD])',
        r'the answer is.*?([ABCD])',
        r'therefore.*?([ABCD])',
        r'conclusion.*?([ABCD])',
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look for isolated letters at the end
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Check for "A)", "B)", etc.
        if re.match(r'^([ABCD])\)?\s*$', line):
            return re.match(r'^([ABCD])\)?\s*$', line).group(1)
    
    # Strategy 4: Look for the last meaningful occurrence of option letters
    # But avoid false positives from chemical formulas, etc.
    sentences = re.split(r'[.!?]', response)
    for sentence in reversed(sentences):
        # Look for letters that appear to be answer choices
        words = sentence.split()
        for word in reversed(words):
            if word.strip() in ['A', 'B', 'C', 'D']:
                return word.strip()
    
    # Strategy 5: Last resort - find any occurrence of A, B, C, or D
    all_letters = re.findall(r'\b([ABCD])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    # Default fallback
    logging.warning(f"Could not extract answer from response")
    return "A"