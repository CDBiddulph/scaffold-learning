import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """
    Process a multiple choice science question and return the answer letter.
    """
    try:
        logging.info("Processing multiple choice science question")
        
        # System prompt to prime the LLM for scientific reasoning
        system_prompt = (
            "You are an expert scientist with deep knowledge in physics, chemistry, "
            "biology, astronomy, and mathematics. Answer multiple choice questions "
            "by reasoning step-by-step, then provide your final answer in the exact "
            "format 'Answer: <letter>' where the letter is A, B, C, or D."
        )
        
        # Get LLM response
        response = execute_llm(input_string, system_prompt=system_prompt)
        logging.info(f"Received LLM response ({len(response)} characters)")
        
        # Extract the answer using the expected "Answer: <letter>" format
        answer_pattern = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_pattern:
            answer = answer_pattern.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback 1: Look for "The answer is <letter>" pattern
        fallback_pattern = re.search(r'the answer is\s*([A-D])', response, re.IGNORECASE)
        if fallback_pattern:
            answer = fallback_pattern.group(1).upper()
            logging.info(f"Using fallback pattern 1, answer: {answer}")
            return answer
        
        # Fallback 2: Find the last occurrence of a standalone letter A-D
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Using fallback pattern 2, answer: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        return "A"