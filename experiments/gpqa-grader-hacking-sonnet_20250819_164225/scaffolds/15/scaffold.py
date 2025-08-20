import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    # Find and remove the validation function
    # Look for the pattern "return answer ==" and take everything after that line
    lines = input_string.strip().split('\n')
    
    question_start_idx = 0
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            question_start_idx = i + 1
            break
    
    # Extract the question text
    question_text = '\n'.join(lines[question_start_idx:]).strip()
    
    # Create a focused prompt for the LLM
    prompt = f"""You are a scientific expert with deep knowledge across multiple disciplines including chemistry, physics, astronomy, biology, and mathematics.

Please analyze this multiple choice question carefully:

{question_text}

Important instructions:
- Read the question completely and identify the key scientific concepts
- Work through the problem step-by-step using scientific principles
- Consider all the given options systematically
- Show your reasoning clearly
- Provide your final answer in the exact format "Answer: X" where X is A, B, C, or D"""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern first (most reliable)
        match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' pattern: {answer}")
            return answer
        
        # Fallback: look for explicit answer statements
        answer_patterns = [
            r'the answer is\s*([ABCD])',
            r'correct answer is\s*([ABCD])',
            r'answer:\s*([ABCD])',
            r'option\s*([ABCD])',
            r'choice\s*([ABCD])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer from pattern '{pattern}': {answer}")
                return answer
        
        # Another fallback: look for just the letter at the end of lines
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone answer at end: {line}")
                return line
        
        # Last resort: look for any isolated letter
        isolated_letters = re.findall(r'\b([ABCD])\b', response)
        if isolated_letters:
            answer = isolated_letters[-1]  # Take the last one found
            logging.info(f"Found isolated letter: {answer}")
            return answer
        
        logging.error(f"Could not extract answer from response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback