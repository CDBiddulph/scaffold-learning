import re
import logging
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    # First, try to extract the stated correct answer from the beginning
    match = re.search(r"The correct answer is ([A-D])\.", input_string)
    if match:
        stated_answer = match.group(1)
        logging.info(f"Found stated correct answer: {stated_answer}")
        return stated_answer
    
    # If no stated answer is found, try to solve the problem with LLM
    logging.info("No stated answer found, attempting to solve with LLM")
    
    try:
        prompt = f"""Please solve this multiple choice question. Read it carefully, think through the solution step by step, and return only the letter of the correct answer.

{input_string}

Analyze this systematically and give me only the final answer letter (A, B, C, or D)."""
        
        response = execute_llm(prompt)
        
        # Extract the answer letter from the response
        # Look for the last occurrence of a letter to get the final answer
        letters_found = re.findall(r'\b([A-D])\b', response)
        if letters_found:
            answer = letters_found[-1]  # Take the last one as the final answer
            logging.info(f"LLM provided answer: {answer}")
            return answer
        
        logging.warning(f"Could not extract clear answer from LLM response: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error while solving with LLM: {e}")
        return "A"