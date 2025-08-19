import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(response):
    """Extract the answer letter from LLM response using multiple patterns"""
    
    # Look for "Answer: <letter>" patterns first (most reliable)
    answer_patterns = [
        r'Answer:\s*([A-D])',
        r'Answer:\s*&lt;([A-D])&gt;',
        r'Answer:\s*<([A-D])>',
        r'Final answer:\s*([A-D])',
    ]
    
    for pattern in answer_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()  # Take the last match
    
    # Look in the last few lines for common answer patterns
    lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
    
    for line in reversed(lines[-5:]):  # Check last 5 non-empty lines
        # Direct letter match
        if line.upper() in ['A', 'B', 'C', 'D']:
            return line.upper()
            
        # Letter in parentheses
        match = re.search(r'\(([A-D])\)', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
            
        # "The answer is X" pattern
        match = re.search(r'answer is ([A-D])', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
            
        # "I choose/select X" pattern
        match = re.search(r'(?:choose|select)\s+([A-D])', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        # "Option X" pattern
        match = re.search(r'option\s+([A-D])', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Last resort: look for any standalone letters in the entire response
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()  # Take the last one found
    
    logging.warning("Could not extract answer letter from response, defaulting to A")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing multiple choice science question")
        
        # Check timeout buffer
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Pass the input directly to LLM - it already contains step-by-step instructions
        response = execute_llm(input_string.strip())
        logging.info(f"Received LLM response of {len(response)} characters")
        
        answer_letter = extract_answer_letter(response)
        logging.info(f"Extracted final answer: {answer_letter}")
        
        return answer_letter
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback