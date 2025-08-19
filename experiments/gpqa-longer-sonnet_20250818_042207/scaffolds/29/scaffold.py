import logging
import re
import time
from llm_executor import execute_llm

def extract_answer(response: str) -> str:
    """Extract the answer letter from the LLM response using multiple methods"""
    
    # Look for "Answer: X" pattern (case insensitive)  
    answer_matches = re.findall(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_matches:
        answer = answer_matches[-1].upper()
        logging.info(f"Extracted answer using 'Answer:' pattern: {answer}")
        return answer
    
    # Look for alternative answer patterns
    alt_patterns = [
        r'(?:the answer is|answer is)\s*([A-D])',
        r'(?:final answer|my answer).*?([A-D])', 
        r'(?:I choose|choose|select).*?([A-D])',
        r'(?:option|choice).*?([A-D])'
    ]
    
    for pattern in alt_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            answer = matches[-1].upper()
            logging.info(f"Extracted answer using alternative pattern: {answer}")
            return answer
    
    # Look for letters in parentheses like (A), (B)
    paren_matches = re.findall(r'\(([A-D])\)', response)
    if paren_matches:
        answer = paren_matches[-1].upper()
        logging.info(f"Extracted answer from parentheses: {answer}")
        return answer
    
    # Last resort: find any A, B, C, or D and take the last one
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        answer = letters[-1].upper()
        logging.warning(f"Using last mentioned letter as answer: {answer}")
        return answer
    
    logging.error("Could not extract any answer letter from response")
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 115  # Leave 5 seconds buffer for processing
    
    try:
        logging.info("Processing multiple choice scientific question")
        
        # Quick validation
        if not re.search(r'[A-D]\)', input_string):
            logging.warning("Input format may be unexpected - no standard A), B), C), D) options found")
        
        # Check timeout before expensive operations
        if time.time() - start_time > max_time:
            logging.error("Timeout reached before LLM call")
            return "A"
        
        # System prompt to guide the LLM's scientific reasoning
        system_prompt = """You are an expert scientist with deep knowledge across multiple scientific disciplines including biology, chemistry, physics, astronomy, and mathematics.

For this multiple choice question:
- Carefully analyze each option using established scientific principles
- Use systematic reasoning to eliminate incorrect options
- Select the most scientifically accurate answer
- Follow the formatting instruction exactly as specified in the question"""

        # Call the LLM to analyze the question
        response = execute_llm(input_string, system_prompt)
        
        # Check timeout after LLM call
        if time.time() - start_time > max_time:
            logging.warning("Timeout reached after LLM call, proceeding with extraction")
        
        # Extract and return the answer letter
        answer = extract_answer(response)
        logging.info(f"Successfully extracted final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Exception occurred while processing: {str(e)}")
        return "A"  # Safe default fallback