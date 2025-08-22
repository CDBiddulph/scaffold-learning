import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the actual question (skip validation function)
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after the validation function)
        question_start = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                question_start = i + 1
                break
        
        question_text = '\n'.join(lines[question_start:]).strip()
        
        logging.info(f"Processing question: {question_text[:200]}...")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # The questions already include proper instructions for format
        # Use LLM to solve the scientific question
        response = execute_llm(question_text)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer using multiple strategies
        
        # Primary: Look for "Answer: X" format (as requested in questions)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in required format: {answer}")
            return answer
        
        # Fallback patterns for common response formats
        fallback_patterns = [
            r'The answer is\s*([A-D])',
            r'final answer.*?([A-D])',
            r'correct answer.*?([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
            r'Therefore,?\s*([A-D])',
            r'\b([A-D])\)\s*(?:is|would be|appears to be)'
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer using fallback pattern '{pattern}': {answer}")
                return answer
        
        # Final fallback: Look for any standalone A, B, C, or D near the end
        # Split into sentences and look for letters in the last few sentences
        sentences = re.split(r'[.!?]+', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            letters = re.findall(r'\b([A-D])\b', sentence)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Found answer in sentence analysis: {answer}")
                return answer
        
        # Ultimate fallback: Any A-D in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        # If absolutely no answer found, default to A
        logging.warning("No answer pattern found in response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default