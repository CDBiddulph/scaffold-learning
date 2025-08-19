import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second limit
    
    try:
        # Remove the validation function from the input if present
        lines = input_string.strip().split('\n')
        question_lines = []
        
        for line in lines:
            if line.startswith('def validate_answer'):
                break
            if line.startswith('# Internal validation'):
                continue
            question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached before processing")
            return "A"
        
        # Check if question already has formatting instructions
        if "Think step-by-step" in question and "Answer:" in question:
            prompt = question
        else:
            # Add formatting instructions if not present
            prompt = f"""{question}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
        
        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached after LLM call")
            return "A"
        
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract answer using multiple patterns
        patterns = [
            r'Answer:\s*([ABCD])',  # Primary pattern
            r'answer:\s*([ABCD])',  # Case insensitive
            r'final answer.*?([ABCD])',  # "final answer is A"
            r'The answer is\s*([ABCD])',
            r'correct answer.*?([ABCD])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # Fallback: look for standalone letters in last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):
            # Look for isolated A, B, C, or D
            matches = re.findall(r'\b([ABCD])\b', line.strip())
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found fallback answer: {answer}")
                return answer
        
        # Final fallback
        logging.warning("Could not extract answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"