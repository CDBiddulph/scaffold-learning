import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info(f"Processing scientific question of length {len(input_string)}")
        
        # Check timeout early
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # System prompt to establish scientific expertise context
        system_prompt = """You are an expert scientist with deep knowledge across all scientific disciplines including physics, chemistry, biology, astronomy, quantum mechanics, molecular biology, organic chemistry, particle physics, and mathematics. You excel at scientific reasoning, calculations, and applying domain-specific knowledge to solve complex problems. 

When answering multiple choice questions, work through the problem systematically, showing your reasoning, then provide your final answer in the exact format "Answer: X" where X is the letter A, B, C, or D."""
        
        logging.info("Sending question to LLM with scientific context")
        response = execute_llm(input_string.strip(), system_prompt=system_prompt)
        
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Primary parsing: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Secondary parsing: Look for "the answer is X" or similar patterns
        answer_patterns = [
            r'the answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'answer:\s*([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Fallback: Find the last isolated letter A, B, C, or D
        # This helps catch cases where the LLM just says "C" at the end
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using fallback extraction, found: {answer}")
            return answer
        
        # Final fallback with more detailed logging
        logging.warning(f"Could not extract answer from response. First 500 chars: {response[:500]}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}", exc_info=True)
        return "A"  # Safe fallback