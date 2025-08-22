import logging
import time
import re
from llm_executor import execute_llm

def extract_answer(response):
    """Extract the answer letter from an LLM response."""
    if not response:
        return None
        
    # Look for "Answer: X" format first since that's what's requested
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Alternative formats
    final_match = re.search(r'final answer is\s*([A-D])', response, re.IGNORECASE)
    if final_match:
        return final_match.group(1).upper()
    
    answer_is_match = re.search(r'the answer is\s*([A-D])', response, re.IGNORECASE)
    if answer_is_match:
        return answer_is_match.group(1).upper()
    
    # Look for just a letter at the end of a line
    response_lines = response.strip().split('\n')
    for line in reversed(response_lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    # Look for option patterns like "A)" near the end
    option_matches = re.findall(r'([A-D])\)', response)
    if option_matches:
        return option_matches[-1]
    
    # Last resort: any A, B, C, or D in the response
    all_letters = re.findall(r'([A-D])', response)
    if all_letters:
        return all_letters[-1]
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120s limit
    
    try:
        logging.info(f"Processing input length: {len(input_string)}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached, returning default answer")
            return "A"
        
        # The input already contains the question, options, and instructions
        # Use a system prompt to encourage careful, expert-level reasoning
        system_prompt = """You are an expert academic with deep knowledge across multiple scientific disciplines including physics, chemistry, biology, astronomy, mathematics, and engineering. Please think carefully and systematically about each question, analyzing each option thoroughly before choosing your answer. Use your expertise to provide accurate, well-reasoned responses."""
        
        logging.info("Sending input to LLM")
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached after LLM call")
            return "A"
        
        # Extract the answer from the response
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract answer from LLM response, defaulting to A")
            logging.info(f"Response was: {response[:500]}...")
            return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"