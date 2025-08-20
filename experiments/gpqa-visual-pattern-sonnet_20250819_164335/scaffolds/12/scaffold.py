import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info(f"Processing question (first 200 chars): {input_string[:200]}...")
        
        # Send the question directly to the LLM since it already contains
        # the instruction to think step-by-step
        response = execute_llm(input_string.strip())
        
        elapsed = time.time() - start_time
        logging.info(f"LLM response received in {elapsed:.2f}s")
        
        # Extract the final answer using multiple patterns
        
        # Pattern 1: Look for "Answer: <letter>" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' pattern: {answer}")
            return answer
        
        # Pattern 2: Look for "The answer is A" or similar phrases
        final_answer_match = re.search(r'(?:answer|choice|option|correct)\s+is\s+([A-D])', response, re.IGNORECASE)
        if final_answer_match:
            answer = final_answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'answer is' pattern: {answer}")
            return answer
        
        # Pattern 3: Look for letter in parentheses like (A), (B), etc.
        paren_match = re.search(r'\(([A-D])\)', response)
        if paren_match:
            answer = paren_match.group(1).upper()
            logging.info(f"Extracted answer from parentheses: {answer}")
            return answer
        
        # Pattern 4: Look for just the letter at the end of lines
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(lines):
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer at end of response: {line}")
                return line
        
        # Pattern 5: Look for any single letter A-D in the response
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1]  # Take the last occurrence
            logging.info(f"Extracted last letter found: {answer}")
            return answer
            
        logging.error(f"Could not extract answer from LLM response: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback