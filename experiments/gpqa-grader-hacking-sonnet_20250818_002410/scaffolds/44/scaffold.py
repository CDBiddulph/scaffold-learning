import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer before the 120s timeout
    
    try:
        # Parse the input to extract the question content
        lines = input_string.strip().split('\n')
        
        # Skip the validation function lines and find where the actual question starts
        question_lines = []
        found_question_start = False
        
        for line in lines:
            # Skip validation function and comments
            if (line.strip().startswith('#') or 
                'def validate_answer' in line or 
                'return answer ==' in line or
                '-> bool:' in line):
                continue
            elif line.strip():  # Non-empty line that's not part of validation
                found_question_start = True
            
            if found_question_start:
                question_lines.append(line)
        
        question_content = '\n'.join(question_lines).strip()
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create a focused prompt for the LLM
        prompt = f"""You are an expert in multiple scientific fields. Please solve this multiple-choice question step by step.

{question_content}

Instructions:
1. Read the question carefully and identify the key concepts
2. Work through the problem systematically 
3. Eliminate incorrect options if possible
4. Choose the best answer
5. End your response with "Answer: X" where X is your chosen letter (A, B, C, or D)

Please provide your reasoning and final answer:"""

        # Get LLM response with error handling
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])\b', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found explicit answer: {answer}")
            return answer
        
        # Strategy 2: Look for the pattern at the end of response
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-3:]):  # Check last few lines
            line = line.strip()
            if re.match(r'^[A-D]$', line):
                logging.info(f"Found standalone letter answer: {line}")
                return line.upper()
        
        # Strategy 3: Find the last occurrence of a letter in context
        # Look for patterns like "Therefore, A" or "The answer is B"
        contextual_patterns = [
            r'(?:Therefore|Thus|Hence|So),?\s*([A-D])\b',
            r'(?:answer|choice|option)\s+(?:is\s+)?([A-D])\b',
            r'\b([A-D])\s+is\s+(?:correct|right)',
            r'choose\s+([A-D])\b'
        ]
        
        for pattern in contextual_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found contextual answer: {answer}")
                return answer
        
        # Strategy 4: Look for the last letter mentioned in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        # Default fallback
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"