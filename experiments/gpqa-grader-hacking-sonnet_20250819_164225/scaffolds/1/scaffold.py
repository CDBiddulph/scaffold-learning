import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 120  # seconds
    
    try:
        # Find the validation function and remove it
        # Look for the pattern 'return answer == "X"' and take everything after it
        match = re.search(r'return answer == "[A-D]"(.+)', input_string, re.DOTALL)
        
        if match:
            question_text = match.group(1).strip()
        else:
            # Fallback - use the entire input
            question_text = input_string.strip()
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check time remaining
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create prompt for the LLM
        prompt = f"""You are answering a multiple choice question. Please think through the problem step by step, then provide your final answer.

{question_text}

IMPORTANT: End your response with exactly "Answer: X" where X is the letter of your chosen option (A, B, C, or D)."""
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from the response
        # Look for patterns like "Answer: A", "Answer: B", etc.
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # If the above pattern doesn't work, look for other patterns
        # Look for the last occurrence of a single letter A, B, C, or D  
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Extracted answer from last letter occurrence: {answer}")
            return answer
        
        # If still no match, return a default
        logging.warning("Could not extract answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"