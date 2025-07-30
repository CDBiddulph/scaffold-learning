import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Extract the question content (everything after the metadata)
    metadata_end = input_string.find('</question-metadata>')
    if metadata_end == -1:
        logging.error("Could not find end of question metadata")
        return "A"  # Default fallback
    
    question_content = input_string[metadata_end + len('</question-metadata>'):].strip()
    logging.info(f"Extracted question content: {question_content[:200]}...")  # Log first 200 chars
    
    # Check if we're running out of time
    if time.time() - start_time > 110:  # Leave 10 seconds buffer
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    # Send to LLM
    try:
        response = execute_llm(question_content)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from response using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using Answer: pattern: {answer}")
            return answer
        
        # Strategy 2: Look for the last occurrence of A, B, C, or D as standalone letters
        letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Extracted last standalone letter found: {answer}")
            return answer
        
        # Strategy 3: Look for letters at the very end of the response
        end_match = re.search(r'([ABCD])\s*$', response, re.IGNORECASE | re.MULTILINE)
        if end_match:
            answer = end_match.group(1).upper()
            logging.info(f"Extracted letter at end: {answer}")
            return answer
        
        # Strategy 4: Look for letters in parentheses like (A) or (B)
        paren_match = re.search(r'\(([ABCD])\)', response, re.IGNORECASE)
        if paren_match:
            answer = paren_match.group(1).upper()
            logging.info(f"Extracted letter in parentheses: {answer}")
            return answer
            
        logging.error("Could not extract any answer from response")
        return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback