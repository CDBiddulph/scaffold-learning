import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # The input should be a multiple choice question
        # Extract the question text
        question_text = input_string.strip()
        
        logging.info(f"Processing question of length {len(question_text)}")
        
        # Create a prompt that asks the LLM to solve the question step by step
        prompt = f"""Please answer this multiple choice question. Think through it step by step and provide your reasoning, then give your final answer in the format "Answer: <letter>".

{question_text}"""
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Get LLM response
        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern
        answer_pattern = r"Answer:\s*([A-D])"
        matches = re.findall(answer_pattern, response, re.IGNORECASE)
        
        if matches:
            answer = matches[-1].upper()  # Take the last match and convert to uppercase
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # If no clear "Answer: X" format, look for other patterns
        # Look for final letter at end of response
        final_letter_pattern = r"\b([A-D])\b(?!.*\b[A-D]\b)"
        matches = re.findall(final_letter_pattern, response)
        if matches:
            answer = matches[0].upper()
            logging.info(f"Extracted final letter: {answer}")
            return answer
        
        # Look for any letter in the response as fallback
        any_letter_pattern = r"\b([A-D])\b"
        matches = re.findall(any_letter_pattern, response)
        if matches:
            answer = matches[-1].upper()  # Take the last occurrence
            logging.info(f"Extracted last letter occurrence: {answer}")
            return answer
        
        # If we still can't find an answer, try a more aggressive approach
        # Ask the LLM to just give us the letter
        if time.time() - start_time > 110:
            logging.warning("Timeout approaching, returning default")
            return "A"
            
        logging.warning("Could not extract answer from first response, trying simplified prompt")
        simple_prompt = f"""What is the answer to this multiple choice question? Respond with only the letter A, B, C, or D.

{question_text}"""
        
        simple_response = execute_llm(simple_prompt)
        
        # Extract single letter from simple response
        letter_match = re.search(r"\b([A-D])\b", simple_response)
        if letter_match:
            answer = letter_match.group(1).upper()
            logging.info(f"Extracted answer from simple prompt: {answer}")
            return answer
        
        # Last resort: return most common answer from training data
        logging.error(f"Could not extract any valid answer. LLM responses were: '{response}' and '{simple_response}'")
        return "C"  # Slightly most common in examples
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        # Return a reasonable default
        return "A"