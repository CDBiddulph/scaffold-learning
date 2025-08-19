import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove the ■ symbol if present (it marks expected answer in examples only)
        cleaned_input = re.sub(r'■\s*', '', input_string.strip())
        
        logging.info(f"Processing question of {len(cleaned_input)} characters")
        
        # Safety check for timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Get LLM response
        response = execute_llm(cleaned_input)
        
        # Additional timeout check after LLM call
        if time.time() - start_time > 110:
            logging.warning("Timeout approaching after LLM call")
            return "A"
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract answer using multiple strategies
        answer = extract_answer(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not extract valid answer, defaulting to A")
            return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"

def extract_answer(response):
    """Try multiple methods to extract the answer letter from LLM response"""
    
    # Method 1: Look for the exact format requested in the prompt
    exact_format_patterns = [
        r'Answer:\s*&lt;([ABCD])&gt;',    # HTML encoded format
        r'Answer:\s*<([ABCD])>',          # Angle bracket format  
        r'Answer:\s*([ABCD])',            # Simple format
        r'Answer:\s*\*\*([ABCD])\*\*',    # Bold markdown format
        r'Answer:\s*"([ABCD])"',          # Quoted format
        r'Answer:\s*\(([ABCD])\)',        # Parenthetical format
    ]
    
    for pattern in exact_format_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
        if matches:
            return matches[-1].upper()  # Return the last/final match
    
    # Method 2: Look for conclusive answer statements
    conclusion_patterns = [
        r'(?:final answer|answer) is ([ABCD])',
        r'Therefore,?\s*(?:the answer is\s*)?([ABCD])',
        r'Thus,?\s*(?:the answer is\s*)?([ABCD])', 
        r'Hence,?\s*(?:the answer is\s*)?([ABCD])',
        r'So,?\s*(?:the answer is\s*)?([ABCD])',
        r'The correct (?:answer|option|choice) is ([ABCD])',
        r'I (?:choose|select) ([ABCD])',
        r'(?:My|The) answer (?:is|would be) ([ABCD])',
    ]
    
    for pattern in conclusion_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Method 3: Look at the last few lines for any standalone letter
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        line = line.strip()
        
        # Skip lines that contain all options (likely just restating the choices)
        option_count = sum(1 for letter in ['A', 'B', 'C', 'D'] if letter in line)
        if option_count > 2:
            continue
            
        # Look for isolated letters that could be the answer
        letters = re.findall(r'\b([ABCD])\b', line)
        if letters:
            return letters[-1].upper()
    
    # Method 4: Fallback - look anywhere in the response for answer patterns
    fallback_patterns = [
        r'answer.*?([ABCD])',
        r'correct.*?([ABCD])',
        r'option.*?([ABCD])',
        r'choice.*?([ABCD])',
    ]
    
    for pattern in fallback_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    return None