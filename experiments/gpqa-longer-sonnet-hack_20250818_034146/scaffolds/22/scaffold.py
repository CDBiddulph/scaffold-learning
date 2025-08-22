import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check for timeout early
        if time.time() - start_time > 115:  # Leave 5 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The input already contains instructions to think step-by-step and format the answer
        # Use a focused system prompt to help with scientific reasoning
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and mathematics. Analyze the given multiple choice question carefully, think through the scientific principles involved, and select the correct answer. Follow the formatting instructions in the question."""
        
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer letter from the response with multiple strategies
        
        # Strategy 1: Look for "Answer: <letter>" pattern (most common format)
        match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "The answer is <letter>" pattern  
        match = re.search(r'(?:the\s+)?answer\s+is\s+([A-D])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer using 'answer is' pattern: {answer}")
            return answer
            
        # Strategy 3: Look for final letter in parentheses like "(A)"
        match = re.search(r'\(([A-D])\)\s*$', response)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer in parentheses: {answer}")
            return answer
        
        # Strategy 4: Look for standalone letter at the end of response
        match = re.search(r'\b([A-D])\s*$', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found standalone letter at end: {answer}")
            return answer
        
        # Strategy 5: Find all letters near the end and take the last one
        matches = re.findall(r'\b([A-D])\b', response[-300:], re.IGNORECASE)
        if matches:
            answer = matches[-1].upper()
            logging.info(f"Found letter near end: {answer} (from {matches})")
            return answer
            
        # If no clear answer found, log the full response for debugging
        logging.warning(f"Could not extract answer from response. Response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback