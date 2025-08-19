import logging
import re
import time
from llm_executor import execute_llm

def extract_answer(response):
    """Extract answer from LLM response."""
    # First try to find explicit "Answer: X" format
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Fallback: look for the last occurrence of a single letter A-D at word boundary
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1]
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check if we're already close to timeout
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Remove the instruction at the end if present
        text = re.sub(r'Think step-by-step.*$', '', input_string, flags=re.DOTALL).strip()
        
        # First attempt with detailed reasoning request
        prompt = f"""You are an expert scientist with deep knowledge across all scientific fields. Please solve this multiple choice question step-by-step.

{text}

Please think through this problem carefully, showing your reasoning step by step. Consider all relevant scientific principles, formulas, and concepts. Then provide your final answer in the exact format: "Answer: <letter>" where <letter> is A, B, C, or D.
"""
        
        logging.info("Sending question to LLM (first attempt)")
        response = execute_llm(prompt)
        logging.info("LLM response received")
        
        answer = extract_answer(response)
        if answer:
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Second attempt with simpler instructions if first attempt failed
        if time.time() - start_time < 90:  # Still have time for second attempt
            logging.info("First attempt failed to extract answer, trying second attempt")
            prompt2 = f"""Please solve this scientific question and choose the correct answer.

{text}

Analyze this step by step and then state your final answer as: Answer: <letter>
"""
            response2 = execute_llm(prompt2)
            answer = extract_answer(response2)
            if answer:
                logging.info(f"Extracted answer on second attempt: {answer}")
                return answer
        
        logging.warning("Could not extract answer from either attempt")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback