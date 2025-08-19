import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    logging.info("Processing academic multiple choice question")
    
    # Remove any existing instruction text to avoid confusion
    clean_input = re.sub(r'Think step-by-step.*?Answer:\s*<letter>.*?$', '', input_string, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # Create a clear, focused prompt
    prompt = f"{clean_input}\n\nSolve this academic question step by step. After your analysis, provide your final answer in the format: Answer: X (where X is A, B, C, or D)"
    
    # Check timeout safety
    if time.time() - start_time > 100:  # Leave buffer time
        logging.warning("Approaching timeout, returning default answer")
        return 'A'
    
    try:
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Extract answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([ABCD])',                    # Answer: A
            r'answer\s*is\s*([ABCD])',                # answer is A  
            r'final\s*answer\s*is\s*([ABCD])',        # final answer is A
            r'correct\s*answer\s*is\s*([ABCD])',      # correct answer is A
            r'choose\s*([ABCD])',                     # choose A
            r'select\s*([ABCD])',                     # select A
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # Fallback: look for single letters at the end of the response
        lines = [line.strip() for line in response.strip().split('\n')]
        for line in reversed(lines[-5:]):  # Check last 5 lines
            if line.upper() in ['A', 'B', 'C', 'D']:
                logging.info(f"Fallback extraction: {line.upper()}")
                return line.upper()
        
        # Another fallback: look for option format like "(A)" or "A)"
        option_patterns = [
            r'\(([ABCD])\)',   # (A)
            r'([ABCD])\)',     # A)
        ]
        
        for pattern in option_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Option format extraction: {answer}")
                return answer
        
        logging.warning("Could not extract answer from response, defaulting to A")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return 'A'