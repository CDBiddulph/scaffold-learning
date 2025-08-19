import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer for timeout
    
    try:
        # Parse the input to extract question and options
        question_text, options = parse_question_and_options(input_string)
        
        if not question_text or len(options) != 4:
            logging.error(f"Failed to parse question properly. Question: {bool(question_text)}, Options: {len(options)}")
            return "A"  # Default fallback
        
        logging.info(f"Question: {question_text[:100]}...")
        logging.info(f"Options count: {len(options)}")
        
        # Check timeout before expensive LLM call
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout reached before LLM call")
            return "A"
        
        # Create comprehensive prompt for LLM
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering. Solve this multiple choice question step by step.

Question:
{question_text}

Options:
A) {options[0]}
B) {options[1]}
C) {options[2]}
D) {options[3]}

Instructions:
1. Carefully analyze the question and identify the key scientific concepts involved
2. Work through any necessary calculations or reasoning step by step
3. Consider all relevant scientific principles, formulas, and relationships
4. Evaluate each option systematically
5. Provide your final answer as just the letter (A, B, C, or D)

Show your work clearly, then end your response with "Final Answer: [LETTER]" where [LETTER] is A, B, C, or D."""

        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the final answer
        answer = extract_answer(response)
        
        logging.info(f"Extracted answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback

def parse_question_and_options(input_string: str) -> tuple:
    """Parse the input to extract question text and multiple choice options."""
    
    lines = [line.rstrip() for line in input_string.split('\n')]
    
    # Find where the validation function ends and question begins
    question_start = -1
    in_function = False
    
    for i, line in enumerate(lines):
        # Skip validation function
        if 'def validate_answer' in line:
            in_function = True
            continue
        elif in_function and line.strip().startswith('return answer'):
            in_function = False
            continue
        elif in_function:
            continue
        
        # Skip comments and empty lines
        if line.strip().startswith('#') or not line.strip():
            continue
            
        # This should be the start of the question
        if not in_function and line.strip():
            question_start = i
            break
    
    if question_start == -1:
        logging.error("Could not find question start")
        return "", []
        
    # Find where options start (first line starting with "A)")
    options_start = -1
    for i in range(question_start, len(lines)):
        if lines[i].strip().startswith('A)'):
            options_start = i
            break
            
    if options_start == -1:
        logging.error("Could not find options starting with A)")
        return "", []
        
    # Extract question text
    question_lines = []
    for i in range(question_start, options_start):
        line = lines[i].strip()
        if line:  # Include non-empty lines
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    
    # Extract options A, B, C, D
    options = ["", "", "", ""]  # Initialize
    current_option = -1
    
    for i in range(options_start, len(lines)):
        line = lines[i].strip()
        
        if line.startswith('A)'):
            current_option = 0
            options[0] = line[2:].strip()
        elif line.startswith('B)'):
            current_option = 1
            options[1] = line[2:].strip()
        elif line.startswith('C)'):
            current_option = 2
            options[2] = line[2:].strip()
        elif line.startswith('D)'):
            current_option = 3
            options[3] = line[2:].strip()
        elif line.startswith('Think step-by-step'):
            break
        elif current_option != -1 and line and not line.startswith(('A)', 'B)', 'C)', 'D)')):
            # Continue previous option on next line
            options[current_option] += " " + line
    
    # Clean up options
    options = [opt.strip() for opt in options]
    
    return question_text, options

def extract_answer(response: str) -> str:
    """Extract the final answer letter from the LLM response."""
    
    # Look for "Final Answer: X" pattern (most reliable)
    final_answer_match = re.search(r'Final Answer:\s*([ABCD])', response, re.IGNORECASE)
    if final_answer_match:
        return final_answer_match.group(1).upper()
    
    # Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
        
    # Look for common answer patterns
    answer_patterns = [
        r'The answer is\s*([ABCD])',
        r'Therefore,?\s*([ABCD])',
        r'So the answer is\s*([ABCD])',
        r'^([ABCD])$',  # Just a letter on its own line
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).upper()
    
    # Fall back to finding the last standalone letter
    letters = re.findall(r'\b([ABCD])\b', response)
    if letters:
        return letters[-1].upper()
    
    logging.warning(f"Could not extract answer from response: {response[:300]}...")
    return "A"  # Default fallback