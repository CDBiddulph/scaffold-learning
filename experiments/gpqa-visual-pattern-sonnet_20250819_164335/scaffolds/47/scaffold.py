import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120s timeout
    
    try:
        # Send the entire input to LLM with clear instructions
        prompt = f"""You are answering a multiple choice scientific/technical question. Please analyze the question carefully and select the best answer.

{input_string}

Please think through this step by step:
1. Understand what the question is asking
2. Analyze each answer option carefully
3. Apply relevant scientific principles and knowledge
4. Eliminate incorrect options
5. Choose the best answer

Provide your final answer as only the letter: A, B, C, or D"""

        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the letter from response
        response_upper = response.upper().strip()
        
        # Look for final answer patterns in order of preference
        patterns = [
            r'FINAL ANSWER:\s*([ABCD])',
            r'ANSWER:\s*([ABCD])',
            r'THE ANSWER IS\s*([ABCD])',
            r'I CHOOSE\s*([ABCD])',
            r'CORRECT ANSWER:\s*([ABCD])',
            r'MY ANSWER:\s*([ABCD])',
            r'\b([ABCD])\s*$',  # Letter at the very end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_upper)
            if match:
                answer = match.group(1)
                logging.info(f"Selected answer using pattern '{pattern}': {answer}")
                return answer
        
        # Look for the last occurrence of A, B, C, or D in the response
        letters = re.findall(r'\b([ABCD])\b', response_upper)
        if letters:
            answer = letters[-1]
            logging.info(f"Selected answer from last occurrence: {answer}")
            return answer
            
        # Check each line from bottom up for a standalone letter
        lines = response_upper.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer as standalone line: {line}")
                return line
                
        # Last resort - look for any mention of letters
        if 'A' in response_upper:
            return 'A'
        elif 'B' in response_upper:
            return 'B' 
        elif 'C' in response_upper:
            return 'C'
        elif 'D' in response_upper:
            return 'D'
                
        logging.warning(f"Could not extract answer from response: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback