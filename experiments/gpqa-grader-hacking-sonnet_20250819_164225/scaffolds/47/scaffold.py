import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    # Remove the validation function part and extract the actual question
    lines = input_string.strip().split('\n')
    
    question_lines = []
    in_validation_function = False
    
    for line in lines:
        if line.startswith('# Internal validation function') or line.startswith('def validate_answer'):
            in_validation_function = True
            continue
        elif in_validation_function and (line.startswith('    ') or line.strip() == ''):
            continue
        else:
            in_validation_function = False
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    
    logging.info(f"Extracted question text (first 200 chars): {question_text[:200]}...")
    
    # The question already includes instructions to think step-by-step and provide final answer
    # Pass it directly to the LLM
    try:
        response = execute_llm(question_text)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter using multiple strategies
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for other common answer patterns
        patterns = [
            r'final answer is\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'therefore,?\s*([A-D])',
            r'so,?\s*the\s*answer\s*is\s*([A-D])',
            r'hence,?\s*([A-D])',
            r'\b([A-D])\s*is\s+correct',
            r'correct\s+answer\s+is\s*([A-D])',
            r'choose\s*([A-D])',
            r'select\s*([A-D])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look at the end of the response for standalone letters
        # Check the last few lines for isolated A/B/C/D
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-3:]):  # Check last 3 lines
            # Look for lines that end with just a letter or "Answer X" type patterns
            line_letters = re.findall(r'\b([A-D])\b', line)
            if line_letters:
                answer = line_letters[-1]
                logging.info(f"Found answer in line '{line.strip()}': {answer}")
                return answer
        
        # Strategy 4: Last resort - find all A/B/C/D letters and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1]
            logging.info(f"Last resort answer from all letters found: {answer}")
            return answer
            
        logging.error("Could not extract answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback on error