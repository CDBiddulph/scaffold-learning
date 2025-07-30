import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the question content after metadata
        metadata_end = input_string.find('</question-metadata>')
        if metadata_end == -1:
            logging.error("Could not find end of metadata section")
            return "A"
        
        question_content = input_string[metadata_end + len('</question-metadata>'):].strip()
        
        logging.info(f"Processing question of length: {len(question_content)}")
        
        # Check time limit - leave buffer for processing
        if time.time() - start_time > 100:
            logging.warning("Approaching time limit early")
            return "A"
        
        # The question already contains proper instructions to think step-by-step
        # and format the answer, so pass it directly to the LLM
        response = execute_llm(question_content)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" format (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Strategy 2: Look for other common answer patterns
        answer_patterns = [
            r'final\s+answer\s*:?\s*([A-D])',  # "final answer: X" or "final answer X"
            r'the\s+answer\s+is\s+([A-D])',   # "the answer is X"
            r'correct\s+answer\s*:?\s*([A-D])', # "correct answer: X"
            r'option\s+([A-D])',               # "option X"
            r'choice\s+([A-D])',               # "choice X"
            r'\b([A-D])\)\s*$'                 # "X)" at end of line
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for any A-D letters in the last part of the response
        # This is less reliable but better than nothing
        last_part = response[-200:]  # Check last 200 characters
        letters = re.findall(r'\b([A-D])\b', last_part)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer letter in response tail: {answer}")
            return answer
        
        # Strategy 4: If all else fails, try to re-prompt with clearer instructions
        if time.time() - start_time < 110:  # Still have time
            logging.warning("Could not extract answer, trying clarification prompt")
            
            clarification_prompt = f"""Based on your previous analysis, what is the single letter answer (A, B, C, or D)?

Previous response: {response[-500:]}

Respond with just the letter A, B, C, or D."""
            
            clarification_response = execute_llm(clarification_prompt)
            
            letter_match = re.search(r'\b([A-D])\b', clarification_response)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Got answer from clarification: {answer}")
                return answer
        
        logging.warning("All extraction strategies failed, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe default