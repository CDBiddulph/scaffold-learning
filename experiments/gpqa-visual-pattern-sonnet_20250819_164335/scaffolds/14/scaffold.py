import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(text):
    """Extract answer letter from text using multiple strategies."""
    # Strategy 1: Look for exact "Answer: X" format (most reliable)
    match = re.search(r"Answer:\s*([A-D])", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 2: Look for common answer patterns
    patterns = [
        r"(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])",
        r"(?:therefore|thus|hence|so),?\s*(?:the\s+)?answer\s+(?:is\s+)?([A-D])",
        r"(?:final\s+)?(?:answer|choice|option):\s*([A-D])",
        r"([A-D])\s*(?:is\s+(?:the\s+)?(?:correct|right)\s*(?:answer|choice|option)?)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Return the last match (most likely to be final answer)
            return matches[-1].upper()
    
    # Strategy 3: Look for standalone letters, preferring those near the end
    letter_matches = list(re.finditer(r'\b([A-D])\b', text, re.IGNORECASE))
    if letter_matches:
        # Return the last occurrence, most likely the final answer
        return letter_matches[-1].group(1).upper()
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 110  # Leave 10 second buffer for timeout
    
    try:
        logging.info("Processing multiple choice question")
        
        # The input already contains proper instructions, send directly to LLM
        logging.info("Sending question to LLM for step-by-step analysis...")
        response = execute_llm(input_string.strip())
        
        elapsed = time.time() - start_time
        logging.info(f"LLM response received after {elapsed:.2f}s")
        
        # Extract answer from response
        answer = extract_answer_letter(response)
        
        if answer and answer in 'ABCD':
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If extraction failed and we have time, try clarification
        if elapsed < max_time - 8:  # Need at least 8 seconds for clarification
            logging.info("Answer extraction failed, requesting clarification...")
            
            clarify_prompt = f"""You just provided a detailed analysis of a multiple choice question. 
Based on your analysis: {response[-400:]}

Please provide just your final answer as a single letter: A, B, C, or D"""
            
            try:
                clarify_response = execute_llm(clarify_prompt)
                logging.info(f"Clarification response: {clarify_response}")
                
                # Extract from clarification
                clarify_answer = extract_answer_letter(clarify_response)
                if clarify_answer and clarify_answer in 'ABCD':
                    logging.info(f"Extracted answer from clarification: {clarify_answer}")
                    return clarify_answer
                    
                # Simple character scan as final fallback for clarification
                for char in clarify_response.upper():
                    if char in 'ABCD':
                        logging.info(f"Found answer letter in clarification: {char}")
                        return char
                        
            except Exception as e:
                logging.warning(f"Clarification failed: {e}")
        
        # Final fallback - return A as default
        logging.warning("Failed to extract definitive answer, using default 'A'")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe default