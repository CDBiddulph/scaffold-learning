import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing scientific multiple choice question")
    
    try:
        # Use a system prompt to reinforce the LLM's role as a scientific expert
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and mathematics. Solve the given multiple choice question step by step, then provide your final answer in the exact format requested."""
        
        # Send the question to the LLM (it already contains formatting instructions)
        response = execute_llm(input_string, system_prompt=system_prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract the answer using multiple strategies for robustness
        
        # Primary strategy: Look for "Answer: <letter>" pattern
        match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' format: {answer}")
            return answer
        
        # Backup strategy: Look for single letter on its own line (search from end)
        lines = response.strip().split('\n')
        for line in reversed(lines):
            clean_line = line.strip()
            if clean_line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found single letter answer on line: {clean_line}")
                return clean_line
        
        # Additional strategy: Look for final answer pattern
        match = re.search(r'final answer.*?([ABCD])', response, re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer using 'final answer' pattern: {answer}")
            return answer
        
        # Last resort: Find the last isolated occurrence of A, B, C, or D
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1]
            logging.info(f"Using last isolated letter found: {answer}")
            return answer
        
        # If all extraction methods fail, log the response and default to A
        logging.warning("Could not extract answer from response")
        logging.warning(f"Response preview: {response[:300]}...")
        return 'A'
        
    except Exception as e:
        logging.error(f"Exception occurred while processing: {str(e)}")
        return 'A'