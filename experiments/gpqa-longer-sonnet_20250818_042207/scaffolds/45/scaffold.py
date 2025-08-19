import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120s limit
    
    try:
        logging.info("Processing multiple choice question")
        
        # Check if we're running out of time
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "Answer: A"
        
        # First attempt - use the input as provided since it already contains step-by-step instructions
        response = execute_llm(input_string)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer
        answer_letter = extract_answer(response)
        if answer_letter:
            logging.info(f"Successfully extracted answer: {answer_letter}")
            return f"Answer: {answer_letter}"
        
        # Check timeout before second attempt
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, using fallback")
            return "Answer: A"
        
        # Second attempt with more explicit formatting instructions
        logging.warning("Could not extract clear answer, trying with explicit instructions")
        
        explicit_prompt = f"""
{input_string}

IMPORTANT: You must end your response with exactly "Answer: X" where X is one of A, B, C, or D.
"""
        
        response2 = execute_llm(explicit_prompt)
        logging.info(f"Second response received, length: {len(response2)}")
        
        answer_letter = extract_answer(response2)
        if answer_letter:
            logging.info(f"Extracted answer from second attempt: {answer_letter}")
            return f"Answer: {answer_letter}"
        
        # Check timeout before third attempt
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching after second attempt")
            return "Answer: A"
        
        # Third attempt - ask for just the letter
        logging.warning("Still no clear answer, asking for just the letter")
        
        simple_prompt = f"""
Based on this question, what is the correct answer?

{input_string}

Respond with only the single letter: A, B, C, or D
"""
        
        response3 = execute_llm(simple_prompt)
        logging.info(f"Third response: {response3}")
        
        # Look for any single letter in the response
        letter_match = re.search(r'\b([A-D])\b', response3.strip(), re.IGNORECASE)
        if letter_match:
            answer_letter = letter_match.group(1).upper()
            logging.info(f"Found letter in third attempt: {answer_letter}")
            return f"Answer: {answer_letter}"
        
        # Last resort fallback
        logging.error("Could not determine answer after multiple attempts")
        return "Answer: A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "Answer: A"

def extract_answer(response: str) -> str:
    """Extract answer letter from LLM response using multiple strategies"""
    
    # Strategy 1: Look for exact "Answer: <letter>" format
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for common answer phrases
    answer_patterns = [
        r'the correct answer is\s*([A-D])',
        r'the answer is\s*([A-D])',
        r'final answer:\s*([A-D])',
        r'final answer is\s*([A-D])',
        r'correct answer:\s*([A-D])',
        r'correct option is\s*([A-D])',
        r'option\s*([A-D])\s*is\s*correct',
        r'choice\s*([A-D])\s*is\s*correct',
        r'therefore,?\s*([A-D])',
        r'thus,?\s*([A-D])',
        r'so,?\s*([A-D])',
        r'answer:\s*([A-D])',
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look for letters at the end of the response (likely conclusion)
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        letter_match = re.search(r'\b([A-D])\b', line, re.IGNORECASE)
        if letter_match:
            return letter_match.group(1).upper()
    
    # Strategy 4: Find the last occurrence of any letter A-D
    letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
    if letters:
        return letters[-1].upper()
    
    return None