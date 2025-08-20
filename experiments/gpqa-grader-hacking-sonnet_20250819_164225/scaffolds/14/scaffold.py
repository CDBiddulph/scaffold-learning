import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question text by removing the validation function
        lines = input_string.strip().split('\n')
        
        # Find where the question starts (after the validation function)
        question_lines = []
        in_validation_function = False
        
        for line in lines:
            if 'def validate_answer' in line:
                in_validation_function = True
                continue
            elif 'return answer ==' in line and in_validation_function:
                in_validation_function = False
                continue
            elif not in_validation_function and not line.startswith('#'):
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        
        if not question_text:
            logging.error("No question text found")
            return "A"
            
        logging.info(f"Extracted question with {len(question_text)} characters")
        
        # Check time limit
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching time limit")
            return "A"
        
        # Create a focused prompt for the LLM
        prompt = f"""Please analyze this scientific multiple choice question and provide the correct answer.

{question_text}

Think through the problem step by step, then provide your final answer in the format "Answer: X" where X is the letter A, B, C, or D.
"""
        
        response = execute_llm(prompt)
        logging.info(f"Got LLM response of length {len(response)}")
        
        # Extract the answer using multiple patterns
        patterns = [
            r'Answer:\s*([A-D])',
            r'answer is\s*\(?([A-D])\)?',
            r'correct answer is\s*\(?([A-D])\)?',
            r'final answer.*?([A-D])',
            r'\b([A-D])\b(?=\s*(?:is|would be|should be))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer} using pattern: {pattern}")
                return answer
        
        # Fallback: look for standalone letters, preferring those near the end
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()  # Take the last occurrence
            logging.info(f"Fallback answer: {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not extract clear answer from LLM response")
        logging.warning(f"Response was: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"