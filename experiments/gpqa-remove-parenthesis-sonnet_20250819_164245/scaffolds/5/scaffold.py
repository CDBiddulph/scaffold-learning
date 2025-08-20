import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """Process a scientific multiple choice question and return the answer letter."""
    
    start_time = time.time()
    
    try:
        question = input_string.strip()
        logging.info(f"Processing question of length {len(question)}")
        
        # Timeout check - leave buffer for processing
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning fallback")
            return "A"
        
        # Create a comprehensive prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, and astronomy. 

Please solve this multiple choice question:

{question}

Instructions:
1. Read the question carefully and identify the scientific concepts involved
2. Analyze each answer choice systematically
3. Apply relevant scientific principles, formulas, and reasoning
4. Show your step-by-step analysis
5. Choose the best answer based on scientific evidence
6. End with "Answer: X" where X is A, B, C, or D

Please provide your analysis:"""

        logging.info("Sending question to LLM...")
        response = execute_llm(prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract the answer using multiple robust methods
        
        # Method 1: Look for explicit "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Method 2: Look for other common answer expressions
        answer_patterns = [
            r'the\s+(?:correct\s+)?answer\s+is\s*(?:option\s+)?([ABCD])',
            r'(?:option|choice)\s*([ABCD])\s+is\s+(?:the\s+)?(?:correct|right)',
            r'therefore,?\s*(?:the\s+answer\s+is\s+)?([ABCD])',
            r'so\s+(?:the\s+answer\s+is\s+)?([ABCD])',
            r'final\s+answer:?\s*([ABCD])',
            r'answer.*?([ABCD])(?:\s|$)',
            r'select\s+(?:option\s+)?([ABCD])',
            r'choose\s+(?:option\s+)?([ABCD])'
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last occurrence
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Method 3: Find standalone letters, preferring those near the end
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Extracted answer using last letter method: {answer}")
            return answer
            
        # If all extraction methods fail, log and return fallback
        logging.error(f"Could not extract answer from response. First 500 chars: {response[:500]}...")
        return "A"  # Fallback to A
        
    except Exception as e:
        logging.error(f"Exception occurred while processing: {str(e)}")
        return "A"  # Fallback answer