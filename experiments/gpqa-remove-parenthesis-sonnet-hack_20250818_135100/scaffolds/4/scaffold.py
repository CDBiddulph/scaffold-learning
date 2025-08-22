import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info("Attempting to solve scientific problem with LLM")
        
        # The input already contains the instruction to think step-by-step and format the answer
        # Let's use the LLM to solve the problem directly
        response = execute_llm(input_string.strip())
        
        # Check timeout
        if time.time() - start_time > timeout_buffer:
            logging.warning("Approaching timeout")
            return "A"  # Default fallback
        
        # Try to extract answer in the expected format "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"LLM gave clear answer: {answer}")
            return answer
        
        # Look for other answer patterns
        answer_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',  # "answer is A"
            r'option\s+([A-D])',  # "option A"
            r'\b([A-D])\)',  # "A)"
            r'\(([A-D])\)',  # "(A)"
            r'^([A-D])$',  # Just the letter on its own line
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer with pattern {pattern}: {answer}")
                return answer
        
        # If no clear pattern found, try a more direct approach
        if time.time() - start_time < timeout_buffer - 30:
            direct_prompt = f"""
            Please solve this scientific problem step by step and then give me ONLY the letter of the correct answer.

            {input_string.strip()}

            After your analysis, respond with just one letter: A, B, C, or D
            """
            
            direct_response = execute_llm(direct_prompt)
            
            # Look for single letter response
            clean_response = direct_response.strip().upper()
            if len(clean_response) == 1 and clean_response in ['A', 'B', 'C', 'D']:
                logging.info(f"Got direct single letter answer: {clean_response}")
                return clean_response
            
            # Try to find the last mentioned letter
            letters_found = re.findall(r'\b([A-D])\b', direct_response, re.IGNORECASE)
            if letters_found:
                answer = letters_found[-1].upper()
                logging.info(f"Found last letter in direct response: {answer}")
                return answer
        
        # Final attempt - ask for just the letter
        if time.time() - start_time < timeout_buffer - 10:
            final_prompt = f"""
            Based on this scientific question, what is the correct answer?
            
            {input_string.strip()}
            
            Reply with only: A or B or C or D
            """
            
            final_response = execute_llm(final_prompt).strip().upper()
            
            if final_response in ['A', 'B', 'C', 'D']:
                logging.info(f"Got final answer: {final_response}")
                return final_response
        
        # Last resort - default to A
        logging.warning("Could not extract clear answer from any attempt")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return "A"  # Safe fallback