import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Give ourselves some buffer
    
    try:
        # Parse the input to extract just the question
        lines = input_string.strip().split('\n')
        
        # Find where the question starts (after the validation function)
        question_start = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                # This is the last line of the validation function
                question_start = i + 1
                break
        
        # Skip any empty lines
        while question_start < len(lines) and not lines[question_start].strip():
            question_start += 1
            
        # Extract the question
        question_lines = lines[question_start:]
        question_text = '\n'.join(question_lines)
        
        logging.info(f"Extracted question (first 300 chars): {question_text[:300]}...")
        
        # Check if we're running out of time
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout")
            return "A"
        
        # Solve using LLM with system prompt for scientific expertise
        system_prompt = "You are an expert in multiple scientific disciplines including physics, chemistry, biology, and astronomy. Solve problems step by step with scientific rigor and precision."
        
        response = execute_llm(question_text, system_prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer - look for "Answer: X" pattern first
        answer_pattern = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_pattern:
            answer = answer_pattern.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' format: {answer}")
            return answer
        
        # Look for final answer patterns
        final_patterns = [
            r'(?:final answer|answer).*?([ABCD])',
            r'(?:therefore|thus|so).*?([ABCD])',
            r'(?:the answer is|answer is).*?([ABCD])'
        ]
        
        for pattern in final_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Fallback: look for the last letter mentioned in the response
        letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter found: {answer}")
            return answer
            
        # Final fallback
        logging.warning("No answer found in response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return A as safe default
        return "A"