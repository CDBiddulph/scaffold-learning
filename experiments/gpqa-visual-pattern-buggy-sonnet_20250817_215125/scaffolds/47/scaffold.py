import logging
import re
import time
from llm_executor import execute_llm

def parse_question(input_string):
    """Parse the input to extract question and options"""
    # Remove the ■ markings if present, as they won't be in the real test
    input_string = re.sub(r'■\s*', '', input_string)
    
    lines = input_string.strip().split('\n')
    
    # Find where options start (look for A), B), C), D) pattern)
    option_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D]\)', line.strip()):
            option_start = i
            break
    
    if option_start == -1:
        raise ValueError("Could not find options in the input")
    
    # Question is everything before options
    question = '\n'.join(lines[:option_start]).strip()
    
    # Options are from option_start onwards
    options = {}
    current_option = None
    
    for line in lines[option_start:]:
        line = line.strip()
        if not line:
            continue
        # Check if this line starts with an option marker
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            current_option = match.group(1)
            options[current_option] = match.group(2)
        elif current_option:
            # Continuation of current option
            options[current_option] += ' ' + line
    
    return question, options

def get_answer_from_llm(question, options, timeout_remaining):
    """Get answer from LLM with step-by-step reasoning"""
    options_text = "\n".join([f"{key}) {value}" for key, value in options.items()])
    
    prompt = f"""You are answering a scientific multiple choice question. Please think through this step-by-step.

{question}

{options_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
    
    try:
        # Check if we have enough time
        if timeout_remaining < 20:
            logging.warning("Low time remaining, using simplified prompt")
            simple_prompt = f"{question}\n\n{options_text}\n\nAnswer:"
            response = execute_llm(simple_prompt)
        else:
            response = execute_llm(prompt)
        
        logging.info(f"LLM response: {response[:200]}...")
        
        # Extract the answer using multiple patterns
        patterns = [
            r'Answer:\s*([A-D])',
            r'(?:The answer is|answer is)\s*([A-D])',
            r'(?:Therefore|Thus|So),?\s*(?:the answer is)?\s*([A-D])',
            r'(?:^|\n)([A-D])(?:\s|$)',  # Letter at start of line or standalone
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).upper()
        
        # Fallback: look for the last occurrence of A, B, C, or D
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            return letters[-1].upper()
            
        return None
        
    except Exception as e:
        logging.error(f"Error getting LLM response: {e}")
        return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Parse the input
        question, options = parse_question(input_string)
        
        logging.info(f"Parsed question: {question[:100]}...")
        logging.info(f"Found options: {list(options.keys())}")
        
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > timeout:
            logging.warning("Timeout reached during parsing, returning A")
            return "A"
        
        # Get answer from LLM
        timeout_remaining = timeout - elapsed
        answer = get_answer_from_llm(question, options, timeout_remaining)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Selected answer: {answer}")
            return answer
        
        # If we couldn't get a valid answer, return A as fallback
        logging.warning("Could not extract valid answer from LLM response, returning A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"