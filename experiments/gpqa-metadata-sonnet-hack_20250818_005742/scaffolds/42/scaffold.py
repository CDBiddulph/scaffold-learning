import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the question
        lines = input_string.strip().split('\n')
        
        # Find where the question starts (after the </question-metadata> tag)
        question_start = -1
        for i, line in enumerate(lines):
            if '</question-metadata>' in line:
                question_start = i + 1
                break
        
        if question_start == -1:
            logging.error("Could not find end of question metadata")
            return "A"  # Default fallback
        
        # Extract the question text
        question_text = '\n'.join(lines[question_start:]).strip()
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check if we're approaching timeout
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use LLM to answer the question - most questions already end with proper instructions
        response = execute_llm(question_text)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the answer using multiple patterns to handle various response formats
        patterns = [
            r'Answer:\s*([ABCD])',           # Standard format requested in questions
            r'Final answer:\s*([ABCD])',     # Alternative format
            r'The answer is\s*([ABCD])',     # Natural language format
            r'([ABCD])\)',                   # Format like "A)"
            r'option\s+([ABCD])',           # "option A" format
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Fallback: look for any single letter A, B, C, or D in the last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer at end of response: {line}")
                return line
        
        # Final fallback: try a more targeted follow-up question
        if time.time() - start_time < 100:  # Only if we have time
            logging.warning("Could not extract clear answer, trying follow-up")
            follow_up_prompt = f"""Based on your previous analysis, what is your final answer to this multiple choice question? Respond with only the letter A, B, C, or D.

Previous response: {response[-500:]}"""  # Include last part of previous response
            
            follow_up_response = execute_llm(follow_up_prompt)
            follow_up_response = follow_up_response.strip().upper()
            
            if follow_up_response in ['A', 'B', 'C', 'D']:
                logging.info(f"Got answer from follow-up: {follow_up_response}")
                return follow_up_response
        
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback