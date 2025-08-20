import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Process a multiple choice scientific question and return the correct answer letter.
    """
    try:
        # Call the LLM with the input (which already contains the question and instructions)
        response = execute_llm(input_string)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response
        answer = extract_answer_from_response(response)
        if answer:
            return answer
            
        # If we couldn't extract an answer, try again with a more explicit prompt
        logging.warning("Could not extract answer, trying again with explicit prompt")
        
        explicit_prompt = f"""Please solve this multiple choice question and respond with your reasoning followed by exactly "Answer: X" where X is A, B, C, or D.

{input_string}"""
        
        response2 = execute_llm(explicit_prompt)
        logging.info(f"Second LLM response: {response2}")
        
        answer = extract_answer_from_response(response2)
        if answer:
            return answer
            
        logging.error("Could not extract answer from either response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_answer_from_response(response: str) -> str:
    """
    Extract the answer letter from an LLM response using multiple strategies.
    """
    # Strategy 1: Look for "Answer: X" pattern (most reliable)
    answer_pattern = r"Answer:\s*<?([A-D])>?"
    match = re.search(answer_pattern, response, re.IGNORECASE)
    
    if match:
        answer = match.group(1).upper()
        logging.info(f"Extracted answer with 'Answer:' pattern: {answer}")
        return answer
    
    # Strategy 2: Look for lines that are just a single letter (from the end)
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            logging.info(f"Found standalone answer line: {line}")
            return line
    
    # Strategy 3: Look for choice patterns like "A)" or "(A)" 
    choice_patterns = [
        r'\b([A-D])\)',  # A), B), etc.
        r'\(([A-D])\)',  # (A), (B), etc.
        r'\b([A-D])\.',  # A., B., etc.
    ]
    
    for pattern in choice_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            answer = matches[-1].upper()  # Take the last match
            logging.info(f"Found answer with pattern {pattern}: {answer}")
            return answer
    
    # Strategy 4: Look for isolated letters in the final portion of text
    # Split into sentences and check the last few
    sentences = re.split(r'[.!?]', response)
    for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
        single_letters = re.findall(r'\b([A-D])\b', sentence)
        if single_letters:
            answer = single_letters[-1].upper()
            logging.info(f"Found answer in sentence: {answer}")
            return answer
    
    logging.warning("Could not extract answer using any strategy")
    return None