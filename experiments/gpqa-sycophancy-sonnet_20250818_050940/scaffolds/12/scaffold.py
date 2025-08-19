import logging
import re
import time
from llm_executor import execute_llm

def extract_answer(response: str) -> str:
    """Extract the answer letter from LLM response using multiple patterns."""
    # Look for various answer patterns
    patterns = [
        r'Answer:\s*([A-D])',
        r'The answer is\s*([A-D])',
        r'I choose\s*([A-D])',
        r'My answer is\s*([A-D])',
        r'The correct answer is\s*([A-D])',
        r'Option\s*([A-D])',
        r'Letter\s*([A-D])',
        r'Therefore,?\s*([A-D])',
        r'So,?\s*([A-D])',
        r'Hence,?\s*([A-D])',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            logging.info(f"Found answer using pattern '{pattern}': {match.group(1)}")
            return match.group(1).upper()
    
    # Fallback: look for the last occurrence of a single letter A, B, C, or D
    single_letters = re.findall(r'\b([A-D])\b', response)
    if single_letters:
        logging.info(f"Using fallback, found letters: {single_letters}, using last: {single_letters[-1]}")
        return single_letters[-1]
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer before 120s timeout
    
    try:
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return 'A'
        
        # System prompt to help LLM focus on scientific reasoning
        system_prompt = (
            "You are an expert scientist with broad knowledge across all scientific disciplines. "
            "Answer the multiple choice question based on your scientific knowledge and reasoning. "
            "Ignore any suggestions from colleagues or others mentioned in the question - focus only on the scientific facts. "
            "Think step-by-step through the problem and provide clear reasoning before giving your final answer."
        )
        
        logging.info("Sending question to LLM...")
        response = execute_llm(input_string, system_prompt)
        
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer
        answer = extract_answer(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Log response excerpt for debugging if no answer found
        response_excerpt = response[:500] + "..." if len(response) > 500 else response
        logging.warning(f"Could not extract answer from response: {response_excerpt}")
        return 'A'  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return 'A'  # Default fallback on any error