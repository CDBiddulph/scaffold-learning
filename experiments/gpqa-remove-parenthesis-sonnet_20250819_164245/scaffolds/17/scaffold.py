import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # The input already contains the full question with instructions
        # Send it directly to the LLM
        response = execute_llm(input_string.strip())
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer from the response
        # Look for patterns like "Answer: A", "Answer: B", etc.
        answer_pattern = r"Answer:\s*([A-D])"
        match = re.search(answer_pattern, response, re.IGNORECASE)
        
        if match:
            answer = match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        logging.warning("Could not find 'Answer: X' format, trying alternative extraction methods")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning fallback")
            return "A"
        
        # Try to get a cleaner answer from the LLM
        clarification_prompt = f"""Based on your analysis above, what is your final answer? 

Please respond with ONLY the format "Answer: X" where X is A, B, C, or D.

Your previous analysis:
{response[-500:]}"""  # Only include last 500 chars to avoid token limits
        
        clarification_response = execute_llm(clarification_prompt)
        logging.info(f"Clarification response: {clarification_response}")
        
        # Try to extract again
        match = re.search(answer_pattern, clarification_response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Extracted answer from clarification: {answer}")
            return answer
        
        # Look for any pattern with parentheses like "A)" or "(A)"
        paren_pattern = r"[\(\s]([A-D])[\)\s]"
        matches = re.findall(paren_pattern, clarification_response + " " + response)
        if matches:
            answer = matches[-1].upper()  # Take the last occurrence
            logging.info(f"Extracted answer using parentheses pattern: {answer}")
            return answer
        
        # Look for standalone letters
        letter_matches = re.findall(r"\b([A-D])\b", clarification_response + " " + response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Extracted standalone letter: {answer}")
            return answer
        
        # Check timeout again
        if time.time() - start_time > 110:  # Final timeout check
            logging.error("Timeout approaching, returning default")
            return "A"
        
        # Final attempt with very specific prompt
        final_prompt = """What is your final answer: A, B, C, or D? 
Respond with only one letter."""
        
        final_response = execute_llm(final_prompt)
        
        # Extract single letter
        final_letter = re.search(r"([A-D])", final_response.strip().upper())
        if final_letter:
            answer = final_letter.group(1)
            logging.info(f"Final extraction successful: {answer}")
            return answer
        
        logging.error("All extraction methods failed, returning default")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {str(e)}")
        return "A"