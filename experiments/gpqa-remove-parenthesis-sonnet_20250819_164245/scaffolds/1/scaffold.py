import logging
import re
import time
from llm_executor import execute_llm

def extract_answer(response: str) -> str:
    """Extract the final answer from the LLM response."""
    
    # Method 1: Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Method 2: Look for "The answer is X" or similar patterns
    answer_patterns = [
        r'the answer is\s*([A-D])',
        r'correct answer is\s*([A-D])',
        r'final answer.*?([A-D])',
        r'therefore.*?([A-D])',
        r'thus.*?([A-D])',
        r'so.*?([A-D])'
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Method 3: Look for the last standalone letter A-D in parentheses or after option
    option_matches = re.findall(r'(?:option|choice)\s*([A-D])', response, re.IGNORECASE)
    if option_matches:
        return option_matches[-1].upper()
    
    # Method 4: Look for letters followed by closing parenthesis
    paren_matches = re.findall(r'([A-D])\)', response)
    if paren_matches:
        return paren_matches[-1].upper()
    
    # Method 5: Find all standalone A-D patterns and take the last one
    standalone_matches = re.findall(r'\b([A-D])\b', response)
    if standalone_matches:
        return standalone_matches[-1].upper()
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        question = input_string.strip()
        logging.info(f"Processing question of length: {len(question)}")
        
        # Create a comprehensive prompt that encourages step-by-step thinking
        prompt = f"""You are a scientific expert. Solve this multiple choice question step by step.

{question}

Instructions:
1. Read the question carefully and identify the key concepts
2. Work through the problem systematically 
3. Consider each option and eliminate incorrect ones
4. Provide clear reasoning for your final choice
5. End with your answer in the format "Answer: <letter>"

Think step by step:"""

        # Check time before making LLM call
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        # Get the LLM's response
        response = execute_llm(prompt)
        logging.info(f"Got LLM response of length: {len(response)}")
        
        # Extract the answer
        answer = extract_answer(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If we can't extract an answer, try a more direct approach
        if time.time() - start_time < 80:
            logging.info("First attempt failed to extract answer, trying clarification")
            clarification_prompt = f"""Given this question:

{question}

What is the correct answer? Respond with just the letter (A, B, C, or D) and brief justification."""
            
            clarification_response = execute_llm(clarification_prompt)
            logging.info(f"Clarification response: {clarification_response[:200]}...")
            
            answer = extract_answer(clarification_response)
            if answer:
                logging.info(f"Extracted answer from clarification: {answer}")
                return answer
            
            # Try to find just the letter at the start of the response
            first_letter_match = re.search(r'^([A-D])', clarification_response.strip())
            if first_letter_match:
                return first_letter_match.group(1).upper()
                
        # Final fallback
        logging.warning("Could not extract answer from any attempt, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"