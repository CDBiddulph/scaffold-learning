import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_from_response(response: str) -> str:
    """Extract the answer letter from the LLM response."""
    logging.info("Extracting answer from LLM response")
    
    # Look for "Answer: X" format first (most reliable)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        answer = answer_match.group(1).upper()
        logging.info(f"Found answer in standard format: {answer}")
        return answer
    
    # Look for other explicit answer patterns
    patterns = [
        r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
        r'(?:therefore|thus|so|hence),?\s*(?:the\s+answer\s+is\s+)?([A-D])',
        r'option\s+([A-D])\s+is\s+correct',
        r'([A-D])\s+is\s+(?:the\s+)?correct',
        r'choose\s+([A-D])',
        r'select\s+([A-D])',
        r'final\s+answer:\s*([A-D])',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer with pattern '{pattern}': {answer}")
            return answer
    
    # Look for standalone letters at the end of lines (last resort)
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            logging.info(f"Found standalone answer: {line}")
            return line
    
    logging.warning("Could not extract answer, defaulting to A")
    return "A"

def parse_multiple_choice_question(input_string: str):
    """Parse the input to extract question text and options."""
    lines = input_string.strip().split('\n')
    
    options = {}
    question_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is an option line (A), B), etc.)
        # The ■ symbol is just marking the correct answer in examples
        option_match = re.match(r'^■?\s*([A-D])\)\s*(.+)$', line)
        if option_match:
            letter = option_match.group(1)
            text = option_match.group(2)
            options[letter] = text
            logging.info(f"Found option {letter}")
        elif not line.startswith("Think step-by-step"):
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    return question_text, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing multiple choice question")
        
        # Parse the question
        question_text, options = parse_multiple_choice_question(input_string)
        
        if len(options) != 4:
            logging.error(f"Expected 4 options, found {len(options)}: {list(options.keys())}")
            return "A"
        
        logging.info(f"Question length: {len(question_text)} chars")
        
        # Check timeout early
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout during parsing")
            return "A"
        
        # Create focused prompt for LLM
        prompt = f"""Analyze this multiple choice question and select the correct answer:

{question_text}

A) {options['A']}
B) {options['B']}
C) {options['C']}
D) {options['D']}

Think through this step by step, then provide your final answer in the format "Answer: X" where X is the letter (A, B, C, or D) of the correct option."""

        # Use a system prompt to focus the LLM
        system_prompt = "You are an expert in multiple scientific domains. Analyze each question carefully using your knowledge of physics, chemistry, biology, astronomy, and other sciences. Provide clear reasoning and always end with 'Answer: X' format."
        
        logging.info("Querying LLM for answer")
        response = execute_llm(prompt, system_prompt)
        
        # Check timeout before processing response
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout after LLM call")
            return "A"
        
        # Extract answer
        answer = extract_answer_from_response(response)
        
        # Validate answer is one of the valid options
        if answer not in ['A', 'B', 'C', 'D']:
            logging.error(f"Invalid answer extracted: {answer}, defaulting to A")
            answer = "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe default