import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120s limit
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # The input already contains the complete question with instructions
        # to think step-by-step and provide answer in "Answer: <letter>" format
        logging.info("Processing multiple choice science question")
        
        response = execute_llm(input_string)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Primary extraction: Look for "Answer: X" format as instructed
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1)
            logging.info(f"Found answer in 'Answer: X' format: {answer}")
            return answer
        
        # Fallback 1: Look for answer at the end of response
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(lines[-5:]):  # Check last 5 lines
            if re.match(r'^[ABCD]$', line):
                logging.info(f"Found single letter answer at end: {line}")
                return line
        
        # Fallback 2: Look for "final answer" patterns
        final_patterns = [
            r'final answer.*?is\s*([ABCD])',
            r'final answer.*?([ABCD])',
            r'answer.*?is\s*([ABCD])',
            r'correct answer.*?is\s*([ABCD])',
            r'therefore.*?([ABCD])',
            r'thus.*?([ABCD])'
        ]
        
        for pattern in final_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1)
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Fallback 3: Look for any letter followed by closing parenthesis indicating conclusion
        conclusion_match = re.search(r'([ABCD])\)', response)
        if conclusion_match:
            answer = conclusion_match.group(1)
            logging.info(f"Found answer with conclusion pattern: {answer}")
            return answer
            
        # Fallback 4: Count occurrences and return most mentioned letter
        letter_counts = {letter: len(re.findall(r'\b' + letter + r'\b', response)) 
                        for letter in ['A', 'B', 'C', 'D']}
        if any(letter_counts.values()):
            most_common = max(letter_counts, key=letter_counts.get)
            logging.info(f"No clear answer format found, returning most mentioned letter: {most_common}")
            return most_common
            
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Response was: {response[:500]}...")
        
        # Final fallback based on training data distribution
        # A appears most frequently (16/50), so use as ultimate default
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Default to most common answer in training data
        return "A"