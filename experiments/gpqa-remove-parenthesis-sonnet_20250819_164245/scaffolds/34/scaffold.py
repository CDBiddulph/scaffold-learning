import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 100  # Leave buffer for processing
    
    try:
        logging.info(f"Processing input: {input_string[:200]}...")
        
        # First attempt: Pass the full input to the LLM
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        response = execute_llm(input_string)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Try to extract the answer
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Final answer: {answer}")
            return answer
        
        # If no clear answer found, try a second attempt with a more direct prompt
        if time.time() - start_time < timeout - 20:  # Only if we have time
            logging.info("No clear answer found, trying again with direct prompt")
            direct_prompt = f"Based on your previous analysis, what is the single letter answer (A, B, C, or D)?\n\nOriginal question:\n{input_string}\n\nYour previous response:\n{response}\n\nAnswer (single letter only):"
            
            second_response = execute_llm(direct_prompt)
            logging.info(f"Second response: {second_response}")
            
            # Try to extract from the second response
            second_answer = extract_answer(second_response)
            if second_answer:
                logging.info(f"Final answer from second attempt: {second_answer}")
                return second_answer
        
        logging.warning("Could not extract answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_answer(response):
    """Try multiple strategies to extract the answer letter."""
    
    # Strategy 1: Look for "Answer: X" format (most explicit)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        logging.info(f"Found answer in 'Answer:' format: {answer_match.group(1)}")
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "The answer is X" or similar phrases
    context_patterns = [
        r'(?:the )?answer is\s*([A-D])',
        r'(?:the )?correct (?:answer|choice|option) is\s*([A-D])',
        r'(?:choose|select)\s*([A-D])',
        r'(?:option|choice)\s*([A-D])\s*(?:is correct|is the answer)',
        r'therefore[,\s]*([A-D])',
        r'thus[,\s]*([A-D])',
        r'so[,\s]*([A-D])',
    ]
    
    for pattern in context_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            logging.info(f"Found answer in context with pattern '{pattern}': {matches[-1]}")
            return matches[-1].upper()
    
    # Strategy 3: Look for a standalone letter at the end of the response
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if re.match(r'^[A-D]$', line):
            logging.info(f"Found standalone letter: {line}")
            return line.upper()
    
    # Strategy 4: Look for patterns like "A)", "B)", etc. in the conclusion
    # Only look at the last 500 characters to avoid question options
    last_part = response[-500:]
    option_matches = re.findall(r'\b([A-D])\)', last_part)
    if option_matches:
        logging.info(f"Found option pattern: {option_matches[-1]}")
        return option_matches[-1].upper()
    
    # Strategy 5: Look for final conclusion patterns
    conclusion_patterns = [
        r'in conclusion[,\s]*(?:the answer is\s*)?([A-D])',
        r'finally[,\s]*(?:the answer is\s*)?([A-D])',
        r'therefore[,\s]*(?:the answer is\s*)?([A-D])',
    ]
    
    for pattern in conclusion_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            logging.info(f"Found answer in conclusion: {matches[-1]}")
            return matches[-1].upper()
    
    # Strategy 6: Last resort - any letter A-D in the last part
    letter_matches = re.findall(r'\b([A-D])\b', last_part)
    if letter_matches:
        logging.info(f"Found letter in last part: {letter_matches[-1]}")
        return letter_matches[-1].upper()
    
    logging.info("No answer pattern found")
    return None