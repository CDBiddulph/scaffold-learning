import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Leave 5 seconds buffer
    
    try:
        logging.info(f"Processing input: {input_string[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create prompt for LLM
        system_prompt = """You are an expert in multiple scientific fields including physics, chemistry, astronomy, and biology. You have deep knowledge across all these domains and can reason through complex problems step by step."""
        
        prompt = f"""{input_string}

Please analyze this question carefully and provide your reasoning step by step. Then give your final answer in the exact format "Answer: <letter>" where <letter> is A, B, C, or D."""
        
        # Get response from LLM
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response: {response}")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout after LLM call, returning default answer")
            return "A"
        
        # Extract the answer letter
        answer = extract_answer(response)
        logging.info(f"Extracted answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback


def extract_answer(response: str) -> str:
    """Extract the answer letter from the LLM response."""
    
    # Look for "Answer: X" pattern (most explicit and matches the requested format)
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using 'Answer:' pattern")
        return answer_match.group(1).upper()
    
    # Look for "The answer is X" pattern
    answer_match = re.search(r'(?:the\s+)?answer\s+is\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using 'answer is' pattern")
        return answer_match.group(1).upper()
    
    # Look for final answer patterns
    answer_match = re.search(r'final\s+answer[:\s]*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using 'final answer' pattern")
        return answer_match.group(1).upper()
    
    # Look for choice patterns like "Choice A" or "Option A"
    answer_match = re.search(r'(?:choice|option)\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using 'choice/option' pattern")
        return answer_match.group(1).upper()
    
    # Look for patterns like "Therefore, A" or "Thus, B"
    answer_match = re.search(r'(?:therefore|thus|hence),?\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using conclusion pattern")
        return answer_match.group(1).upper()
    
    # Look for standalone letter at end of response
    answer_match = re.search(r'\b([ABCD])\b\.?\s*$', response.strip(), re.IGNORECASE)
    if answer_match:
        logging.info("Found answer as standalone letter at end")
        return answer_match.group(1).upper()
    
    # Split into lines and look for answer in the last few lines
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    for line in reversed(lines[-3:]):  # Check last 3 non-empty lines
        match = re.search(r'\b([ABCD])\b', line)
        if match:
            logging.info(f"Found answer in line: {line}")
            return match.group(1).upper()
    
    # If no clear pattern, look for the last occurrence of A, B, C, or D
    letters = re.findall(r'\b([ABCD])\b', response)
    if letters:
        logging.info(f"Using last occurrence of letter: {letters[-1]}")
        return letters[-1].upper()
    
    # Default fallback
    logging.warning("Could not extract answer from response, defaulting to A")
    return "A"