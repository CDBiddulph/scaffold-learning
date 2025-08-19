import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info(f"Starting to process scientific question of length {len(input_string)}")
        
        # Prepare the prompt to give the LLM space to reason
        prompt = f"""Please solve this scientific multiple choice question step by step.

{input_string}

Analyze the question carefully, apply relevant scientific principles, show your reasoning, and determine the correct answer. 

Provide your final answer in this exact format: "Answer: X" where X is the letter A, B, C, or D."""
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout_buffer:
            logging.warning("Approaching timeout before first LLM call")
            return "A"
        
        # Get LLM response
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract answer using multiple patterns
        answer = extract_answer(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Check timeout before second attempt
        if time.time() - start_time > timeout_buffer:
            logging.warning("Approaching timeout, cannot try second attempt")
            return "A"
        
        # Try a more direct approach if extraction failed
        logging.warning("First attempt failed to extract clear answer, trying direct approach")
        direct_prompt = f"""{input_string}

Based on scientific principles, what is the correct answer? Respond with only the letter A, B, C, or D:"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: '{direct_response.strip()}'")
        
        answer = extract_answer(direct_response)
        if answer:
            logging.info(f"Extracted answer from direct approach: {answer}")
            return answer
        
        # Final fallback
        logging.error("Failed to extract valid answer from both attempts, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception during processing: {e}")
        return "A"

def extract_answer(text):
    """Extract answer letter from LLM response using multiple patterns"""
    patterns = [
        r'Answer:\s*([ABCD])',  # "Answer: A"
        r'answer\s+is\s+([ABCD])',  # "answer is A"  
        r'correct\s+answer\s+is\s+([ABCD])',  # "correct answer is A"
        r'option\s+([ABCD])',  # "option A"
        r'choice\s+([ABCD])',  # "choice A"
        r'Therefore,?\s*([ABCD])',  # "Therefore, A"
        r'([ABCD])\s*is\s*(?:correct|right)',  # "A is correct"
        r'Final\s+answer:?\s*([ABCD])',  # "Final answer: A"
        r'^\s*([ABCD])\s*$',  # Just "A" on its own line
        r'\b([ABCD])\b(?:\s*[.!]?\s*$)',  # Letter at end of text
    ]
    
    # Try each pattern and collect matches
    all_matches = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if match.upper() in ['A', 'B', 'C', 'D']:
                all_matches.append(match.upper())
    
    if all_matches:
        # Return the last match (most likely to be the final answer)
        return all_matches[-1]
    
    # If no pattern matches, look for any isolated A, B, C, or D
    isolated_letters = re.findall(r'\b([ABCD])\b', text)
    if isolated_letters:
        # Return the last one found
        return isolated_letters[-1].upper()
    
    return None