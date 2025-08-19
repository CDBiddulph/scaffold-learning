import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info(f"Processing scientific multiple choice question")
        
        # Create prompt for the LLM - ask it to analyze the question step by step
        prompt = f"""You are answering a multiple choice scientific question. Please analyze this question step by step, showing your reasoning clearly.

{input_string.strip()}

Take your time to think through this carefully. Consider all the scientific principles involved. Provide your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D.
"""
        
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in format 'Answer: {answer}'")
            return answer
        
        # Fallback: look for the last standalone letter A-D in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Fallback: using last letter found: {answer}")
            return answer
            
        # Final fallback if we can't parse anything
        logging.warning(f"Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"