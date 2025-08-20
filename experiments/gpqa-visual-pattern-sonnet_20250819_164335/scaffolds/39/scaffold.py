import logging
import re
import time
from llm_executor import execute_llm

def solve_multiple_choice_question(input_string, attempt=1):
    """Use LLM to solve a multiple choice scientific question"""
    
    if attempt == 1:
        prompt = f"""You are answering a multiple choice scientific question. Please read the question carefully and work through it step by step.

{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""
    else:
        # Second attempt with more direct instructions
        prompt = f"""You are a scientific expert. Solve this multiple choice question and give me the correct letter.

{input_string}

Please end your response with "Answer: X" where X is A, B, C, or D."""

    response = execute_llm(prompt)
    return response

def extract_final_answer(response):
    """Extract the final answer letter from the LLM response"""
    # First, look for explicit "Answer: X" pattern
    answer_pattern = r'Answer:\s*([A-D])'
    match = re.search(answer_pattern, response, re.IGNORECASE)
    
    if match:
        return match.group(1).upper()
    
    # Look for other conclusive patterns
    conclusive_patterns = [
        r'(?:the\s+)?answer\s+is\s+([A-D])',
        r'therefore\s+(?:the\s+answer\s+is\s+)?([A-D])',
        r'so\s+(?:the\s+)?answer\s+is\s+([A-D])',
        r'thus\s+(?:the\s+answer\s+is\s+)?([A-D])',
        r'hence\s+(?:the\s+answer\s+is\s+)?([A-D])',
        r'correct\s+answer\s+is\s+([A-D])',
        r'I\s+choose\s+([A-D])',
        r'final\s+answer:\s*([A-D])',
        r'the\s+correct\s+option\s+is\s+([A-D])',
        r'option\s+([A-D])\s+is\s+correct'
    ]
    
    # Check the last part of the response first (most likely location)
    last_part = response[-500:] if len(response) > 500 else response
    
    for pattern in conclusive_patterns:
        match = re.search(pattern, last_part, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look for any clear indication of the answer in the full response
    for pattern in conclusive_patterns:
        matches = list(re.finditer(pattern, response, re.IGNORECASE))
        if matches:
            # Take the last match
            return matches[-1].group(1).upper()
    
    # Look for standalone letters at the end
    sentences = response.split('.')
    for sentence in reversed(sentences[-5:]):  # Last 5 sentences
        letters = re.findall(r'\b([A-D])\b', sentence.strip())
        if letters:
            return letters[-1]
    
    # Broader search for any letter
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1]
    
    # If all else fails, return A as default
    logging.warning(f"Could not extract answer from response. Returning default 'A'")
    return 'A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120 second timeout
    
    try:
        # First attempt
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return 'A'
            
        response = solve_multiple_choice_question(input_string, attempt=1)
        answer = extract_final_answer(response)
        
        # Validate the answer
        if answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Question solved on first attempt. Answer: {answer}")
            return answer
        
        # If first attempt failed and we have time, try again
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout after first attempt, returning default answer")
            return 'A'
            
        logging.warning("First attempt didn't produce clear answer, trying again...")
        response = solve_multiple_choice_question(input_string, attempt=2)
        answer = extract_final_answer(response)
        
        if answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Question solved on second attempt. Answer: {answer}")
            return answer
        
        # If both attempts failed, return A
        logging.error("Both attempts failed, returning default answer A")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return 'A'