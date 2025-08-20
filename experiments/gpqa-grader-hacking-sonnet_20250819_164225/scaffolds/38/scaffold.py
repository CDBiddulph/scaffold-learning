import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Remove validation function from input if present
    lines = input_string.strip().split('\n')
    clean_lines = []
    skip_mode = False
    
    for line in lines:
        # Skip validation function
        if '# Internal validation function' in line or 'def validate_answer' in line:
            skip_mode = True
            continue
        if skip_mode and (line.strip().startswith('return answer ==') or line.strip().startswith('    return')):
            skip_mode = False
            continue
        if not skip_mode:
            clean_lines.append(line)
    
    question_text = '\n'.join(clean_lines).strip()
    
    # Check if this is a multiple choice question
    has_options = bool(re.search(r'\b[A-D]\)', question_text))
    
    if not has_options:
        logging.info("Not a multiple choice question, processing as open-ended")
        try:
            response = execute_llm(question_text)
            return response.strip()
        except Exception as e:
            logging.error(f"Error processing open-ended question: {e}")
            return "Unable to process question"
    
    logging.info("Processing multiple choice question")
    
    # For multiple choice, we need to be more systematic
    # Use the LLM's domain knowledge but ensure we get a clear answer
    
    try:
        # Check timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout")
            return "A"
        
        # Send to LLM with clear instructions
        prompt = f"""Solve this step-by-step:

{question_text}

Provide your detailed reasoning, then end with exactly "Answer: <letter>" where <letter> is A, B, C, or D."""

        logging.info("Querying LLM for solution")
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Extract the answer using multiple strategies
        
        # Primary: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via primary method: {answer}")
            return answer
        
        # Secondary: Look for common answer patterns
        patterns = [
            r'the answer is\s*([A-D])',
            r'correct answer.*?([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last occurrence
                logging.info(f"Found answer via pattern '{pattern}': {answer}")
                return answer
        
        # Tertiary: Look for isolated letters in the final portion
        final_portion = response[-300:]  # Last 300 characters
        letter_matches = re.findall(r'\b([A-D])\b', final_portion)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Found answer in final portion: {answer}")
            return answer
        
        # Quaternary: Look anywhere for option letters
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Found answer via broad search: {answer}")
            return answer
        
        # If all else fails, try to re-query with simpler prompt
        if time.time() - start_time < 110:
            logging.warning("No answer found, trying simplified prompt")
            simple_prompt = f"""Which option is correct? Just respond with the letter A, B, C, or D.

{question_text}"""
            
            simple_response = execute_llm(simple_prompt)
            simple_match = re.search(r'([A-D])', simple_response)
            if simple_match:
                answer = simple_match.group(1).upper()
                logging.info(f"Found answer via simple prompt: {answer}")
                return answer
        
        logging.error("Could not extract answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing multiple choice question: {e}")
        return "A"  # Safe default