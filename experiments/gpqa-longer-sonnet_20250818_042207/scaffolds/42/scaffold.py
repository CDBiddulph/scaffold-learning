import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(response):
    """Extract the answer letter (A, B, C, or D) from the LLM response."""
    # Look for common patterns where the LLM states its answer
    patterns = [
        r'Answer:\s*([ABCD])',
        r'answer is\s*([ABCD])',  
        r'correct answer is\s*([ABCD])',
        r'option\s*([ABCD])',
        r'choice\s*([ABCD])',
        r'\b([ABCD])\s*is\s*correct',
        r'final answer\s*[:\-]?\s*([ABCD])',
        r'I choose\s*([ABCD])',
        r'select\s*([ABCD])',
        r'pick\s*([ABCD])',
        r'therefore\s*([ABCD])',
        r'so\s*([ABCD])'
    ]
    
    response_upper = response.upper()
    
    for pattern in patterns:
        match = re.search(pattern, response_upper, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Look for the last standalone letter A, B, C, or D in the response
    matches = re.findall(r'\b[ABCD]\b', response_upper)
    if matches:
        return matches[-1]
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 110  # Leave buffer before 120 second timeout
    
    try:
        logging.info("Processing multiple choice academic question")
        
        # Check if we're running out of time
        if time.time() - start_time > max_time:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a comprehensive prompt that encourages step-by-step reasoning
        prompt = f"""You are a knowledgeable academic expert solving a multiple choice question. Please analyze this question carefully and systematically.

{input_string.strip()}

Instructions:
1. Read the question thoroughly
2. Identify what is being asked
3. Consider each answer choice
4. Apply relevant scientific/mathematical principles
5. Show your reasoning step by step
6. State your final answer clearly

Please think through this methodically and end with a clear statement of your answer choice (A, B, C, or D)."""
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"Got LLM response of length: {len(response)}")
        
        # Check timeout again
        if time.time() - start_time > max_time:
            logging.warning("Timeout during LLM call, returning default")
            return "A"
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract clear answer, trying focused fallback")
            
            # Check timeout before fallback
            if time.time() - start_time > max_time:
                logging.warning("No time for fallback, returning default")
                return "A"
            
            # Fallback: ask directly for the answer with minimal context
            fallback_prompt = f"""Analyze this question and respond with only the correct letter (A, B, C, or D):

{input_string.strip()}

Answer:"""
            
            fallback_response = execute_llm(fallback_prompt)
            fallback_answer = extract_answer_letter(fallback_response)
            
            if fallback_answer and fallback_answer in ['A', 'B', 'C', 'D']:
                logging.info(f"Fallback extracted answer: {fallback_answer}")
                return fallback_answer
            else:
                logging.error(f"Could not extract valid answer. Fallback response: {fallback_response[:100]}")
                return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback on error