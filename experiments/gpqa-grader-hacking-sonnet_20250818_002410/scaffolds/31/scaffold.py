import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for safety
    
    try:
        # Clean the input by removing validation function code
        lines = input_string.strip().split('\n')
        cleaned_lines = []
        
        skip_lines = False
        for line in lines:
            line_stripped = line.strip()
            
            # Skip validation function and related code
            if (line_stripped.startswith('#') and 'validation function' in line_stripped.lower()) or \
               line_stripped.startswith('def validate_answer') or \
               (skip_lines and ('return ' in line_stripped or line_stripped == '')):
                skip_lines = True
                if line_stripped == '' and skip_lines:
                    skip_lines = False
                continue
            elif skip_lines:
                continue
            else:
                cleaned_lines.append(line)
        
        cleaned_input = '\n'.join(cleaned_lines).strip()
        
        if not cleaned_input:
            logging.error("No content after cleaning input")
            return "A"
        
        logging.info(f"Processing question of length: {len(cleaned_input)}")
        
        # Check for timeout
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use LLM to solve the scientific question
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and other scientific fields.

Here is a multiple choice scientific question:

{cleaned_input}

Please:
1. Carefully read and understand what is being asked
2. Apply the relevant scientific principles, formulas, or concepts
3. Work through the problem step-by-step
4. Determine which of the given options (A, B, C, or D) is correct

Show your reasoning clearly, then end your response with "FINAL ANSWER: X" where X is the letter of the correct option."""
        
        response = execute_llm(prompt)
        
        if not response:
            logging.error("Empty response from LLM")
            return "A"
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout - 3:
            logging.warning("Near timeout after LLM response")
            return "A"
        
        # Extract the answer using multiple patterns
        answer_patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'answer is\s*([A-D])', 
            r'correct answer is\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'option\s*([A-D])\s*is correct',
            r'choose\s*([A-D])',
            r'select\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: find the last occurrence of A, B, C, or D in the response
        all_letter_matches = re.findall(r'\b([A-D])\b', response)
        if all_letter_matches:
            answer = all_letter_matches[-1].upper()
            logging.info(f"Using last mentioned option as fallback: {answer}")
            return answer
        
        # Final fallback if no patterns match
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {str(e)}")
        return "A"  # Safe fallback