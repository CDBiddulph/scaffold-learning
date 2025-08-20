import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Safety margin before 120s limit
    
    try:
        # Parse input to extract the actual question content
        lines = input_string.strip().split('\n')
        question_start = 0
        
        # Find where the question starts (after the validation function)
        for i, line in enumerate(lines):
            if 'def validate_answer' in line:
                # Look for the end of the function definition
                j = i + 1
                while j < len(lines):
                    current_line = lines[j]
                    # Skip empty lines
                    if not current_line.strip():
                        j += 1
                        continue
                    # If line is not indented, this is where the question starts
                    if not (current_line.startswith('    ') or current_line.startswith('\t')):
                        question_start = j
                        break
                    j += 1
                break
        
        # Extract the question content
        question = '\n'.join(lines[question_start:]).strip()
        
        if not question:
            logging.error("Could not extract question content")
            return "A"
            
        logging.info(f"Extracted question, length: {len(question)}")
        
        # Check timeout before making expensive LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout limit")
            return "A"
            
        # Prepare system prompt to guide the LLM
        system_prompt = ("You are an expert across multiple academic fields including "
                        "biology, chemistry, physics, astronomy, mathematics, and more. "
                        "Read the question carefully, think through it step by step, "
                        "and provide your answer in the exact format requested.")
        
        # Get response from LLM
        response = execute_llm(question, system_prompt)
        
        if not response:
            logging.error("Received empty response from LLM")
            return "A"
            
        logging.info("Received LLM response")
        
        # Extract the answer from the response
        # First, look for the exact format: "Answer: X"
        exact_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if exact_match:
            answer = exact_match.group(1).upper()
            logging.info(f"Found exact format answer: {answer}")
            return answer
        
        # Try alternative formats
        patterns = [
            r'(?:the answer is|answer is|therefore|hence|thus|conclusion:?)\s*([A-D])',
            r'([A-D])\s*(?:is correct|is the correct answer|is right)',
            r'(?:option|choice|letter)\s*([A-D])',
            r'(?:I choose|I select|choose|select)\s*([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern: {answer}")
                return answer
        
        # Look for single letters near the end of the response
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            letters_in_line = re.findall(r'\b([A-D])\b', line)
            if len(letters_in_line) == 1:  # Exactly one letter choice in this line
                answer = letters_in_line[0].upper()
                logging.info(f"Found isolated answer: {answer}")
                return answer
        
        # Final fallback - use the last A-D mentioned in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
            
        # If nothing found, default to A
        logging.warning("Could not extract answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"  # Safe fallback