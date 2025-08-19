import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse input to find where the question starts (after validation function)
        lines = input_string.split('\n')
        
        # Find the end of the validation function by looking for the return statement
        question_start = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                question_start = i + 1
                break
        
        # Extract the question text
        question_text = '\n'.join(lines[question_start:]).strip()
        
        logging.info(f"Extracted question (first 200 chars): {question_text[:200]}...")
        
        # Check for timeout (leave buffer for processing)
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # The question already includes instructions to think step-by-step and format the answer
        # So we can send it directly to the LLM
        response = execute_llm(question_text)
        
        logging.info(f"LLM response (first 300 chars): {response[:300]}...")
        
        # Extract the answer using multiple patterns in order of preference
        extraction_patterns = [
            r'Answer:\s*([A-D])',           # "Answer: A" - primary format
            r'final answer.*?([A-D])',      # "final answer is A" 
            r'answer.*?([A-D])',            # "answer: A" (case insensitive)
            r'\b([A-D])\s*$',               # Letter at end of line
            r'option\s*([A-D])',            # "option A"
            r'choice\s*([A-D])',            # "choice A" 
            r'\(([A-D])\)',                 # "(A)"
        ]
        
        for pattern in extraction_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Final fallback: find all isolated A-D letters and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Fallback: using last letter found: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning(f"Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"