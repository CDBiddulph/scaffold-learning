import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 20  # seconds to leave as buffer
    
    try:
        logging.info("Starting to process scientific multiple choice question")
        
        # Check if we're approaching timeout early
        if time.time() - start_time > 120 - timeout_buffer:
            logging.warning("Approaching timeout before processing, returning default")
            return "A"
        
        # Create a comprehensive prompt that leverages the LLM's scientific knowledge
        prompt = f"""You are an expert scientist solving a multiple choice question. Please analyze the problem carefully, show your step-by-step reasoning, and then provide your final answer in the exact format "Answer: <letter>".

{input_string.strip()}"""
        
        logging.info("Sending request to LLM")
        response = execute_llm(prompt)
        logging.info(f"Received LLM response, length: {len(response)} characters")
        
        # Extract the answer using multiple strategies
        answer = extract_answer_from_response(response)
        
        logging.info(f"Final extracted answer: {answer}")
        return answer
                    
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback

def extract_answer_from_response(response: str) -> str:
    """Extract the multiple choice answer from LLM response using multiple strategies."""
    
    # Strategy 1: Look for "Answer: X" pattern (most reliable)
    answer_pattern = r"Answer:\s*([A-D])"
    match = re.search(answer_pattern, response, re.IGNORECASE)
    if match:
        answer = match.group(1).upper()
        logging.info(f"Found answer using 'Answer:' pattern: {answer}")
        return answer
    
    # Strategy 2: Look for answer in the final lines of response
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        # Look for patterns like "(A)", "A)", or just "A" in short lines
        if len(line.strip()) < 20:  # Short lines more likely to be final answers
            match = re.search(r'\(?([A-D])\)?', line.strip(), re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer in final lines: {answer}")
                return answer
    
    # Strategy 3: Look for choice patterns like "A)", "B)", etc. throughout response
    choice_pattern = r'\b([A-D])\)'
    matches = re.findall(choice_pattern, response)
    if matches:
        answer = matches[-1].upper()  # Take the last occurrence
        logging.info(f"Found answer using choice pattern: {answer}")
        return answer
    
    # Strategy 4: Look for standalone letters A, B, C, D in context
    # Focus on the end of the response where the answer is likely to be
    end_portion = response[-200:]  # Last 200 characters
    letter_pattern = r'\b([A-D])\b'
    matches = re.findall(letter_pattern, end_portion)
    if matches:
        answer = matches[-1].upper()  # Take the last occurrence
        logging.info(f"Found answer using letter pattern in end portion: {answer}")
        return answer
    
    # Strategy 5: More aggressive - any occurrence of A, B, C, D in the entire response
    all_letters = re.findall(r'([A-D])', response, re.IGNORECASE)
    if all_letters:
        answer = all_letters[-1].upper()
        logging.info(f"Found answer using aggressive search: {answer}")
        return answer
    
    logging.warning("Could not extract any valid answer from response, using default")
    return "A"