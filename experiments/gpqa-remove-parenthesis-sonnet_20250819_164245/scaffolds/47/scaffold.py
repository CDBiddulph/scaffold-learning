import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_limit = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        if time.time() - start_time > timeout_limit:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Clean up the input
        question = input_string.strip()
        
        # Prepare the prompt for the LLM
        prompt = f"""You are an expert scientist solving a multiple choice question. Please work through this step-by-step and provide a clear final answer.

{question}

Please think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""
        
        response = execute_llm(prompt)
        logging.info(f"LLM provided response of length: {len(response)}")
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If first attempt failed, try a more direct approach
        if time.time() - start_time > timeout_limit:
            logging.warning("Timeout approaching, returning default")
            return "A"
            
        logging.warning("First extraction failed, trying direct approach")
        direct_prompt = f"""Answer this multiple choice question with just the letter A, B, C, or D:

{question}

Your answer:"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response}")
        
        direct_answer = extract_answer_letter(direct_response)
        if direct_answer and direct_answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Direct extraction successful: {direct_answer}")
            return direct_answer
        
        logging.error("All extraction attempts failed, using default")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return "A"

def extract_answer_letter(text: str) -> str:
    """Extract answer letter from LLM response with multiple strategies"""
    
    if not text:
        return None
    
    text = text.strip()
    
    # Strategy 1: Look for "Answer: X" pattern (most reliable)
    answer_patterns = [
        r"Answer:\s*([ABCD])",
        r"answer:\s*([ABCD])", 
        r"Answer\s*=\s*([ABCD])",
        r"answer\s*=\s*([ABCD])",
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 2: Look at the last few lines for standalone letters
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Check last 3 lines for answer patterns
    for line in lines[-3:]:
        if line.upper() in ['A', 'B', 'C', 'D']:
            return line.upper()
        
        # Check for common answer formats
        line_patterns = [
            r'^([ABCD])\)?\s*$',          # A) or A
            r'^\(([ABCD])\)\s*$',         # (A)
            r'^([ABCD])\.\s*$',           # A.
            r'^Option\s+([ABCD])\s*$',    # Option A
            r'^The answer is\s+([ABCD])\s*$', # The answer is A
            r'^([ABCD])(?:\s|$)',         # A followed by space or end
        ]
        
        for pattern in line_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).upper()
    
    # Strategy 3: Look for any letter following common answer indicators
    indicator_patterns = [
        r"(?:the\s+)?answer\s+is\s+([ABCD])",
        r"(?:choose|select)\s+(?:option\s+)?([ABCD])",
        r"correct\s+(?:answer\s+is\s+|option\s+is\s+)?([ABCD])",
        r"([ABCD])\s+is\s+correct",
        r"option\s+([ABCD])",
    ]
    
    for pattern in indicator_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 4: Look for isolated letters (last resort)
    # Find all single letters A, B, C, D that appear as separate words
    words = re.findall(r'\b[ABCD]\b', text.upper())
    if words:
        # Return the last one found (most likely to be the final answer)
        return words[-1]
    
    return None