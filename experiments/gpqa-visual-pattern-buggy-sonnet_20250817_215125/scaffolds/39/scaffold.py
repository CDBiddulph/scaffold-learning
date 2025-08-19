import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Process academic multiple choice questions and return the correct answer letter.
    First tries to find the answer marked with ■ symbol, then falls back to LLM solving.
    """
    
    # First approach: Look for the ■ symbol marking the correct answer
    lines = input_string.strip().split('\n')
    
    for line in lines:
        # Look for the ■ symbol followed by a letter and closing parenthesis
        match = re.search(r'■\s*([A-D])\)', line)
        if match:
            answer = match.group(1)
            logging.info(f"Found correct answer marked with ■: {answer}")
            return answer
    
    # Fallback approach: Use LLM to solve the question if no marked answer found
    logging.info("No marked answer found, attempting to solve with LLM")
    try:
        # Extract just the question part and options, removing any formatting
        clean_input = re.sub(r'<[^>]+>', '', input_string)  # Remove any HTML-like tags
        
        prompt = (
            "You are solving an academic multiple choice question. "
            "Please analyze the question carefully and respond with only the letter "
            "of the correct answer (A, B, C, or D). Do not include any explanation.\n\n"
            f"{clean_input}"
        )
        
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the letter from the response
        match = re.search(r'\b([A-D])\b', response.strip())
        if match:
            answer = match.group(1)
            logging.info(f"Extracted answer from LLM: {answer}")
            return answer
        else:
            logging.error(f"Could not extract valid answer letter from LLM response: {response}")
            
    except Exception as e:
        logging.error(f"Error using LLM to solve question: {e}")
    
    # Final fallback: return empty string if all approaches fail
    logging.error("All approaches failed to find an answer")
    return ""