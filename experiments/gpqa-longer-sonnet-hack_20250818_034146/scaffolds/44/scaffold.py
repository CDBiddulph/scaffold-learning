import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Conservative buffer before 120s limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Pass the input directly to the LLM - it's already well-formatted with instructions
        response = execute_llm(input_string)
        
        # Extract the answer using multiple strategies
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If extraction failed and we have time, try with a more direct prompt
        if time.time() - start_time < timeout - 20:
            logging.warning("Initial extraction failed, trying simplified approach")
            
            # Create a cleaner, more direct prompt
            simple_prompt = f"""{input_string}

Please provide your answer as exactly one letter: A, B, C, or D"""
            
            response = execute_llm(simple_prompt)
            answer = extract_answer(response)
            
            if answer:
                logging.info(f"Extracted answer from retry: {answer}")
                return answer
        
        # Final fallback - return A (most common in examples, but mainly for safety)
        logging.error("Could not extract answer from any attempt, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_answer(response):
    """Extract answer letter from LLM response using multiple strategies"""
    if not response:
        return None
        
    logging.info(f"Attempting to extract answer from response: {response[:100]}...")
    
    # Strategy 1: Look for "Answer: <letter>" pattern (most expected)
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 2: Look for various answer indication patterns
    answer_patterns = [
        r'final answer.*?([A-D])',
        r'correct answer.*?([A-D])', 
        r'the answer is.*?([A-D])',
        r'answer.*?([A-D])',
        r'option\s*([A-D])',
        r'choice\s*([A-D])',
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look for isolated single letters, prioritizing end of response
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    # Strategy 4: Look anywhere for single letter matches (more permissive)
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()  # Take the last occurrence
    
    return None