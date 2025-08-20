import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 115  # Leave 5 seconds buffer before the 120 second timeout
    
    logging.info(f"Processing question: {input_string[:100]}...")
    
    system_prompt = "You are an expert in all scientific disciplines. Please follow the instructions carefully and provide your answer in the exact format requested."
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > max_time:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern (exact format requested)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # If that fails, look for other common final answer patterns
        answer_match = re.search(r'(?:final answer|the answer|my answer).*?(?:is|:)\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from alternative format: {answer}")
            return answer
        
        # Last resort: find the last A, B, C, or D in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1]
            logging.info(f"Extracted answer from last occurrence: {answer}")
            return answer
        
        logging.error(f"Could not extract answer from response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback