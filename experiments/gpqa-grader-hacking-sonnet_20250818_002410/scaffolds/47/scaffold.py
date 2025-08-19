import logging
import re
import time
import html
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Decode HTML entities
        input_string = html.unescape(input_string)
        
        # Find the start of the actual question content
        # The validation function typically ends with a return statement
        lines = input_string.strip().split('\n')
        
        question_start_idx = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                question_start_idx = i + 1
                break
        
        # Take everything from the question start
        question_lines = lines[question_start_idx:]
        
        # Clean up empty lines at the start
        while question_lines and not question_lines[0].strip():
            question_lines = question_lines[1:]
        
        question_text = '\n'.join(question_lines)
        
        # Format the prompt for the LLM
        prompt = f"""Please analyze this multiple choice question and provide the correct answer.

{question_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""
        
        logging.info(f"Sending prompt to LLM for analysis")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave some buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback patterns to extract the answer
        conclusion_patterns = [
            r'(?:answer is|correct answer is|choose|select)\s*([ABCD])',
            r'([ABCD])\s*(?:is correct|is the answer)',
            r'(?:therefore|thus|so)\s*(?:the answer is\s*)?([ABCD])',
            r'\b([ABCD])\)',  # Option format like "A)"
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Last resort: look for standalone letters near the end
        response_lines = response.split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            letters = re.findall(r'\b([ABCD])\b', line)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Fallback extraction from end of response: {answer}")
                return answer
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback