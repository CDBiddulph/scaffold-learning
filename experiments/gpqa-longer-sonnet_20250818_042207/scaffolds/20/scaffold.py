import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120 second limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Send the input directly to the LLM with expert system prompt
        system_prompt = """You are an expert scientist with deep knowledge across all scientific disciplines including chemistry, biology, physics, astronomy, mathematics, and engineering. Analyze each question carefully, think through the relevant scientific principles, and provide your answer in the exact format requested."""
        
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the answer from the response
        answer = extract_answer(response)
        
        if answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not extract valid answer, using fallback")
            return fallback_answer(response, input_string)
            
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"

def extract_answer(response):
    """Extract the final answer letter from the LLM response"""
    # Look for "Answer: <letter>" pattern (this is the requested format)
    pattern = r"Answer:\s*([A-D])"
    match = re.search(pattern, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for "Answer: &lt;letter&gt;" (HTML encoded format)
    pattern = r"Answer:\s*&lt;([A-D])&gt;"
    match = re.search(pattern, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for "Final Answer: X" pattern
    pattern = r"Final Answer:\s*([A-D])"
    match = re.search(pattern, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return None

def fallback_answer(response, original_input):
    """Extract answer using fallback methods"""
    # Look for patterns like "The answer is A" or "Therefore A"
    patterns = [
        r"(?:the answer is|therefore|thus|hence)\s*([A-D])",
        r"([A-D])\s*(?:is correct|is the answer)",
        r"option\s*([A-D])",
        r"choice\s*([A-D])"
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Look for any single letter A, B, C, D at the end of lines
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        line = line.strip()
        if re.match(r'^[A-D]$', line):
            return line.upper()
    
    # Look for letter in parentheses
    paren_matches = re.findall(r'\(([A-D])\)', response)
    if paren_matches:
        return paren_matches[-1].upper()
    
    # As a last resort, ask the LLM directly for just the letter
    try:
        fallback_prompt = f"""Based on this scientific question:

{original_input}

You previously responded with analysis but I need just the final answer letter. 
Respond with only a single letter: A, B, C, or D"""
        
        fallback_response = execute_llm(fallback_prompt)
        letters = re.findall(r'\b([A-D])\b', fallback_response.strip())
        if letters:
            return letters[0].upper()
    except Exception as e:
        logging.error(f"Fallback LLM call failed: {e}")
    
    return "A"  # Ultimate fallback