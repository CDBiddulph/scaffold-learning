import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Clean the input by removing format instructions if present
        clean_input = input_string.strip()
        if 'Think step-by-step' in clean_input:
            parts = clean_input.split('Think step-by-step')
            clean_input = parts[0].strip()
        
        # Check time remaining
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a comprehensive prompt for scientific analysis
        prompt = f"""You are a world-class scientific expert with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering. Please analyze this multiple choice question carefully.

{clean_input}

Please work through this systematically:
1. Identify the scientific domain and key concepts involved
2. Apply relevant principles, formulas, or theories
3. Analyze each option methodically 
4. Eliminate incorrect choices with reasoning
5. Select the most accurate answer

Conclude with "FINAL ANSWER: X" where X is the correct letter (A, B, C, or D)."""
        
        # Check time before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout before LLM call")
            return "A"
            
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Extract the answer using multiple strategies
        answer = extract_answer(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Check time before backup attempt
        if time.time() - start_time > timeout:
            logging.warning("Timeout before backup attempt")
            return "A"
            
        # Fallback: try a more direct approach
        logging.warning("Primary extraction failed, trying direct approach")
        direct_prompt = f"""Based on your scientific knowledge, what is the correct answer to this question?

{clean_input}

Answer with just the letter (A, B, C, or D): """
        
        direct_response = execute_llm(direct_prompt)
        answer = extract_answer(direct_response)
        if answer:
            logging.info(f"Backup method found answer: {answer}")
            return answer
        
        logging.error("All extraction methods failed")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        return "A"

def extract_answer(response):
    """Extract answer letter from LLM response using multiple patterns"""
    if not response:
        return None
        
    # Try various extraction patterns in order of preference
    patterns = [
        r'FINAL ANSWER:\s*([A-D])',
        r'Answer:\s*([A-D])', 
        r'answer is\s*([A-D])',
        r'correct answer is\s*([A-D])',
        r'therefore\s*([A-D])',
        r'so the answer is\s*([A-D])',
        r'option\s*([A-D])',
        r'choice\s*([A-D])',
        r'select\s*([A-D])',
        r'pick\s*([A-D])',
        r'■\s*([A-D])',  # Handle bullet points
        r'\b([A-D])\s*is correct',
        r'\b([A-D])\s*$'  # Single letter at end of response
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Final fallback: find all isolated A-D letters and take the last one
    # This handles cases where the LLM just states the letter
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    return None