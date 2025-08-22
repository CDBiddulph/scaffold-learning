import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info(f"Processing input length: {len(input_string)}")
        
        # The input is already a well-formatted multiple choice question
        # asking for step-by-step reasoning and final answer as "Answer: <letter>"
        response = execute_llm(input_string)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract answer in "Answer: X" format (case insensitive)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in 'Answer:' format: {answer}")
            return answer
            
        # Fallback 1: Look for lines that are just a single letter
        lines = [line.strip() for line in response.split('\n')]
        for line in reversed(lines):
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found single letter answer: {line}")
                return line
                
        # Fallback 2: Look for isolated A, B, C, or D letters
        isolated_letters = re.findall(r'\b([ABCD])\b', response)
        if isolated_letters:
            answer = isolated_letters[-1]  # Take the last occurrence
            logging.info(f"Found isolated letter: {answer}")
            return answer
            
        # Fallback 3: Look for parentheses format like (A), (B), etc.
        paren_matches = re.findall(r'\(([ABCD])\)', response)
        if paren_matches:
            answer = paren_matches[-1]
            logging.info(f"Found parentheses format: {answer}")
            return answer
            
        # If no answer found, default to A
        logging.warning("Could not extract answer from response, defaulting to A")
        logging.warning(f"Response excerpt: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback