import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    logging.info(f"Processing input: {input_string[:200]}...")
    
    # Check time before calling LLM
    if time.time() - start_time > 100:  # Leave 20 seconds buffer
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    try:
        # Add a system prompt to help the LLM focus on scientific reasoning
        system_prompt = "You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and mathematics. Think step by step and provide clear, accurate reasoning for multiple choice questions."
        
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response length: {len(response)}")
        logging.info(f"LLM response preview: {response[:500]}...")
        
        # Extract the answer from the response using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "Answer <letter>" pattern
        answer_match = re.search(r'Answer\s+([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer letter' pattern: {answer}")
            return answer
        
        # Strategy 3: Look for final answer patterns like "The answer is X" or "Therefore, X"
        final_answer_patterns = [
            r'(?:the answer is|therefore|thus|hence|so the answer is)\s*([A-D])',
            r'([A-D])\s*(?:is correct|is the answer)',
            r'choose\s*([A-D])',
            r'select\s*([A-D])'
        ]
        
        for pattern in final_answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer from pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 4: Look for the last mention of A), B), C), or D)
        option_matches = re.findall(r'([A-D])\)', response)
        if option_matches:
            answer = option_matches[-1].upper()
            logging.info(f"Fallback extracted answer from last option mention: {answer}")
            return answer
        
        # Strategy 5: Look for isolated letters A, B, C, D at the end of lines
        lines = response.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if re.match(r'^[A-D]$', line):
                answer = line.upper()
                logging.info(f"Extracted answer from isolated letter at end of line: {answer}")
                return answer
        
        # Strategy 6: Final fallback - look for any isolated letters A, B, C, D
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Final fallback answer from any letter match: {answer}")
            return answer
        
        logging.warning("No answer pattern found in response")
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
    
    # Ultimate fallback - return A if all else fails
    logging.warning("Could not extract answer, defaulting to A")
    return "A"