import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info(f"Processing academic question...")
        
        # Check timeout
        if time.time() - start_time > max_time:
            logging.error("Timeout approaching, returning default answer")
            return "A"
        
        # Enhanced system prompt
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and related fields. You excel at solving complex academic problems by:

1. Carefully analyzing what the question is asking
2. Identifying the key scientific principles involved
3. Working through calculations and reasoning systematically
4. Evaluating each multiple choice option critically
5. Selecting the most scientifically accurate answer

Be thorough in your analysis but concise in your explanation. Always conclude with "Answer: X" where X is the correct letter."""
        
        # Use LLM to solve the problem
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Check timeout
        if time.time() - start_time > max_time:
            logging.error("Timeout approaching after LLM call")
            return "A"
        
        # Extract the answer - try multiple patterns
        answer_patterns = [
            r'Answer:\s*([ABCD])',
            r'answer:\s*([ABCD])',
            r'Answer\s*([ABCD])',
            r'answer\s*([ABCD])',
            r'final answer.*?([ABCD])',
            r'correct answer.*?([ABCD])',
            r'the answer is.*?([ABCD])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer '{answer}' with pattern: {pattern}")
                return answer
        
        # Fallback: look for the last occurrence of A, B, C, or D
        # that appears to be in an answer context
        lines = response.split('\n')
        for line in reversed(lines):
            match = re.search(r'\b([ABCD])\b', line.upper())
            if match:
                answer = match.group(1)
                logging.info(f"Found answer '{answer}' in line: {line[:50]}...")
                return answer
        
        # Last resort: any A, B, C, D in the response
        all_matches = re.findall(r'\b([ABCD])\b', response.upper())
        if all_matches:
            answer = all_matches[-1]
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Response: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"