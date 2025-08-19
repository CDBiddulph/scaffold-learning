import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing academic multiple choice question")
        
        # Check timeout early
        if time.time() - start_time > 110:  # Leave 10s buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a comprehensive prompt that leverages the LLM's academic knowledge
        prompt = f"""You are an expert academic with comprehensive knowledge across all scientific and technical disciplines including physics, chemistry, biology, astronomy, mathematics, engineering, and related fields.

Please solve this academic question by analyzing it step-by-step:

{input_string}

Please:
1. Identify the key concepts and principles involved
2. Work through the problem systematically
3. Evaluate each answer choice carefully
4. Select the most accurate answer

Think step-by-step to explain your reasoning, then provide your final answer in the exact format: "Answer: <letter>" where <letter> is A, B, C, or D.
"""
        
        response = execute_llm(prompt)
        logging.info(f"Received LLM response (length: {len(response)})")
        
        # Multiple regex patterns to extract the answer reliably
        answer_patterns = [
            r'Answer:\s*([A-D])',  # Primary format requested
            r'(?:Final|Correct)\s+answer:\s*([A-D])',  # Alternative formats
            r'The\s+answer\s+is\s*([A-D])',
            r'\b([A-D])\s+is\s+(?:the\s+)?correct',
            r'Therefore,?\s*([A-D])',
            r'Answer:\s*&lt;([A-D])&gt;'  # Handle HTML entities
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Successfully extracted answer using pattern: {answer}")
                return answer
        
        # Fallback: look for isolated A, B, C, D letters and take the last one
        # This handles cases where the format might be slightly different
        isolated_letters = re.findall(r'\b([A-D])\b', response)
        if isolated_letters:
            answer = isolated_letters[-1].upper()
            logging.warning(f"Using fallback extraction, found: {answer}")
            return answer
        
        # Final fallback
        logging.error("Could not extract any answer from response")
        logging.error(f"Response was: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred while processing: {str(e)}")
        return "A"  # Safe default