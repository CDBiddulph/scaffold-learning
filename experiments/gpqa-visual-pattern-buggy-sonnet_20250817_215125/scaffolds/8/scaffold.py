import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer time
    
    try:
        # Remove example markers (■) that appear in the sample inputs
        clean_input = re.sub(r'■\s*', '', input_string.strip())
        
        # Remove the "Think step-by-step" instruction if present
        clean_input = re.sub(r'\s*Think step-by-step.*$', '', clean_input, flags=re.IGNORECASE | re.DOTALL)
        
        if time.time() - start_time > timeout:
            return "A"
        
        # Use the LLM to analyze and answer the question
        # Send the entire cleaned input and ask for a direct answer
        prompt = f"""You are answering a multiple choice question. Please read the question and answer choices carefully, then select the best answer.

{clean_input}

Please respond with only "Answer: X" where X is the letter (A, B, C, or D) of the correct choice."""

        logging.info("Sending question to LLM for analysis")
        
        if time.time() - start_time > timeout:
            return "A"
        
        response = execute_llm(prompt)
        logging.info(f"Received LLM response")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer: {result}")
            return result
        
        # Backup parsing - look for common answer patterns
        patterns = [
            r'(?:the answer is|I choose|option|choice)\s*([ABCD])',
            r'\b([ABCD])\s*(?:is correct|is the answer|is right)',
            r'^([ABCD])(?:\s|$)',  # Letter at start of line
            r'([ABCD])\)'  # Letter followed by parenthesis
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                result = matches[-1].upper()
                logging.info(f"Found answer via pattern: {result}")
                return result
        
        # Final fallback - any occurrence of A, B, C, or D
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Fallback answer: {result}")
            return result
        
        # Ultimate fallback
        logging.warning("No answer pattern found, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"