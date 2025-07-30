import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120s limit
    
    try:
        # Parse the input to extract the question content
        question_content = extract_question_content(input_string)
        logging.info("Successfully extracted question content")
        
        # Check time remaining
        elapsed = time.time() - start_time
        if elapsed > timeout * 0.8:
            logging.warning("Approaching timeout during parsing")
            return "A"  # Default fallback
        
        # Use LLM to solve the question
        answer = solve_question(question_content, start_time, timeout)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_question_content(input_string: str) -> str:
    """Extract the actual question content from the input string"""
    
    # Find the end of the metadata section
    metadata_end = input_string.find('</question-metadata>')
    if metadata_end != -1:
        content = input_string[metadata_end + len('</question-metadata>'):].strip()
    else:
        # If no metadata found, use the whole content
        logging.warning("No metadata section found, using entire input")
        content = input_string
    
    return content

def solve_question(question_content: str, start_time: float, timeout: float) -> str:
    """Use LLM to solve the question and return the answer letter"""
    
    # Check if we have enough time
    elapsed = time.time() - start_time
    if elapsed > timeout * 0.9:
        logging.warning("Not enough time remaining for LLM call")
        return "A"
    
    try:
        # The question already includes instructions to think step-by-step and provide answer
        response = execute_llm(question_content)
        logging.info("Received LLM response")
        
        # Extract the answer from the response
        answer = extract_answer_from_response(response)
        
        if answer:
            return answer
        else:
            logging.warning("Could not extract answer, trying simplified prompt")
            
            # Check time again before retry
            elapsed = time.time() - start_time
            if elapsed > timeout * 0.95:
                logging.warning("Not enough time for retry")
                return "A"
            
            # Try a more direct prompt
            simple_prompt = f"""Solve this multiple choice question and respond with only the letter A, B, C, or D:

{question_content}

Your answer:"""
            
            simple_response = execute_llm(simple_prompt)
            logging.info("Received simplified LLM response")
            
            simple_answer = extract_answer_from_response(simple_response)
            return simple_answer if simple_answer else "A"
            
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"

def extract_answer_from_response(response: str) -> str:
    """Extract the answer letter from the LLM response"""
    
    # Look for "Answer: <letter>" pattern (case insensitive)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for the letter at the end of a line
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    # Look for isolated letters (word boundaries)
    letter_matches = re.findall(r'\b([A-D])\b', response)
    if letter_matches:
        return letter_matches[-1]  # Return the last occurrence
    
    # Look for any A, B, C, D character
    all_letters = re.findall(r'([A-D])', response)
    if all_letters:
        return all_letters[-1]
    
    return None