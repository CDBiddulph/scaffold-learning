import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Find where the question starts after the validation function
        lines = input_string.strip().split('\n')
        
        question_start_idx = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                question_start_idx = i + 1
                break
        
        # If we didn't find the return statement, try to find end of function another way
        if question_start_idx == 0:
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and not line.startswith('def') and not line.startswith('    '):
                    question_start_idx = i
                    break
        
        # Extract the question
        question = '\n'.join(lines[question_start_idx:]).strip()
        
        if not question:
            logging.error("Could not extract question from input")
            return "A"
        
        logging.info(f"Extracted question length: {len(question)}")
        
        # Use LLM to solve the question
        response = execute_llm(question)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter from the response
        # Look for patterns like "Answer: C" 
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Look for the last occurrence of a single letter A, B, C, or D
        letter_matches = re.findall(r'\b([A-D])\b', response.upper())
        if letter_matches:
            answer = letter_matches[-1]
            logging.info(f"Found answer via last letter: {answer}")
            return answer
        
        # If no clear pattern, try to find any mention of letters
        all_letters = re.findall(r'([A-D])', response.upper())
        if all_letters:
            answer = all_letters[-1]
            logging.info(f"Found answer via any letter: {answer}")
            return answer
        
        logging.error(f"Could not extract answer letter from response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback