import logging
import re
import time
from llm_executor import execute_llm

def extract_answer(response):
    """Extract answer from LLM response using multiple parsing strategies"""
    
    # Strategy 1: Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*<?([A-D])>?', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "The answer is X" pattern  
    answer_match = re.search(r'(?:the answer is|answer is)\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 3: Look for final answer/conclusion patterns
    answer_match = re.search(r'(?:final answer|conclusion|therefore).*?([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 4: Look for standalone letters near the end
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    # Strategy 5: Look for option references like "(A)" or "A)"
    for line in reversed(lines[-10:]):
        for option in ['A', 'B', 'C', 'D']:
            if f'({option})' in line or f'{option})' in line:
                return option
                
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for safety
    
    try:
        # Check for timeout early
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        # Ensure input has clear answer format instructions
        if not re.search(r'answer.*format.*letter', input_string, re.IGNORECASE):
            input_string = input_string.strip() + '\n\nThink step-by-step to solve this problem, then write your final answer in the format "Answer: <letter>".'
            logging.info("Added answer format instruction")
        
        # Main attempt to solve with LLM
        logging.info("Solving question with LLM")
        response = execute_llm(input_string)
        logging.info(f"LLM response length: {len(response)} chars")
        
        answer = extract_answer(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If extraction failed, try asking for clarification
        if time.time() - start_time < timeout - 25:
            logging.info("Initial extraction failed, requesting clarification")
            clarify_prompt = (
                f"Based on this response to a multiple choice question, what is the final answer?\n\n"
                f"Response: {response[-500:]}\n\n"  # Use last 500 chars to focus on conclusion
                f"Please respond with just the letter (A, B, C, or D)."
            )
            clarify_response = execute_llm(clarify_prompt)
            clarify_answer = extract_answer(clarify_response)
            
            if clarify_answer:
                logging.info(f"Clarification provided answer: {clarify_answer}")
                return clarify_answer
        
        # Final fallback: try simpler direct question
        if time.time() - start_time < timeout - 15:
            logging.info("Trying direct approach")
            simple_prompt = f"{input_string}\n\nJust give me the letter of the correct answer: A, B, C, or D?"
            simple_response = execute_llm(simple_prompt)
            simple_answer = extract_answer(simple_response)
            
            if simple_answer:
                logging.info(f"Simple approach gave: {simple_answer}")
                return simple_answer
        
        logging.warning("All extraction methods failed, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe default