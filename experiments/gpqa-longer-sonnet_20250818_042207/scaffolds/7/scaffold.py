import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check timeout early
        if time.time() - start_time > 115:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        logging.info("Processing multiple choice question")
        
        # Use LLM to solve the multiple choice question
        system_prompt = "You are an expert in multiple scientific disciplines. Solve academic questions with careful reasoning."
        
        prompt = f"""Please solve this multiple choice question step by step.

{input_string.strip()}

Analyze the question carefully, show your reasoning, and then provide your final answer in the exact format "Answer: X" where X is the letter A, B, C, or D.
"""
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Primary extraction: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Secondary extraction patterns
        patterns = [
            r'(?:the answer is|correct answer is|final answer is)\s*\(?([A-D])\)?',
            r'(?:option|choice)\s*([A-D])\s*(?:is correct|is right|is the answer)',
            r'therefore\s*(?:the answer is\s*)?([A-D])',
            r'(?:thus|so)\s*(?:the answer is\s*)?([A-D])',
            r'([A-D])\s*(?:is correct|is the correct answer|is right)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Check timeout before trying another approach
        if time.time() - start_time > 100:
            logging.warning("Timeout approaching, using simple fallback")
            letters = re.findall(r'\b([A-D])\b', response)
            if letters:
                return letters[-1].upper()
            return "A"
        
        # If no clear answer found, ask more directly
        logging.info("No clear answer found, asking LLM more directly")
        
        direct_prompt = f"""The following is a multiple choice question. You must respond with exactly one letter: A, B, C, or D.

{input_string.strip()}

What is your answer? Respond with only the letter A, B, C, or D.
"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response.strip()}")
        
        # Look for single letter in direct response
        direct_clean = direct_response.strip().upper()
        if len(direct_clean) == 1 and direct_clean in 'ABCD':
            logging.info(f"Got direct letter response: {direct_clean}")
            return direct_clean
        
        # Extract any letter from direct response
        letter_match = re.search(r'([A-D])', direct_response, re.IGNORECASE)
        if letter_match:
            answer = letter_match.group(1).upper()
            logging.info(f"Extracted letter from direct response: {answer}")
            return answer
        
        # Final fallback: look at end of original response
        response_end = response[-200:]  # Last 200 characters
        letters_at_end = re.findall(r'\b([A-D])\b', response_end)
        if letters_at_end:
            answer = letters_at_end[-1].upper()
            logging.info(f"Using last letter from original response: {answer}")
            return answer
        
        logging.warning("All extraction methods failed, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"