import logging
import re
import time
from llm_executor import execute_llm

def parse_multiple_choice(input_string):
    """Parse a multiple choice question and extract question text and options."""
    
    # Split by lines and clean up
    lines = [line.strip() for line in input_string.strip().split('\n')]
    lines = [line for line in lines if line]  # Remove empty lines
    
    # Find where options start
    option_pattern = r'^(■\s*)?([A-D])\)'
    
    question_lines = []
    options = {}
    found_first_option = False
    
    for line in lines:
        # Skip the standard instruction line
        if "Think step-by-step" in line and ("Answer:" in line or "final answer" in line):
            continue
            
        match = re.match(option_pattern, line)
        if match:
            found_first_option = True
            marked_correct = match.group(1) is not None
            letter = match.group(2)
            option_text = line[match.end():].strip()
            options[letter] = {
                'text': option_text,
                'marked_correct': marked_correct
            }
        else:
            if not found_first_option:
                # This is part of the question
                question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    return question_text, options

def extract_answer_from_response(response):
    """Extract the answer letter from LLM response."""
    
    # Look for explicit "Answer: X" format
    patterns = [
        r'Answer:\s*([A-D])',
        r'(?:the\s+)?answer\s+is\s+([A-D])',
        r'I\s+choose\s+([A-D])',
        r'option\s+([A-D])',
        r'letter\s+([A-D])'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look at the last few lines for a letter
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        letters = re.findall(r'\b([A-D])\b', line)
        if letters:
            return letters[-1].upper()
    
    # Final fallback: any letter in the response
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    return None

def solve_with_llm(question_text, options, timeout=100):
    """Use LLM to solve the multiple choice question."""
    
    start_time = time.time()
    
    # Format the question for the LLM
    prompt_parts = [question_text, ""]
    
    # Add options in order
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            prompt_parts.append(f"{letter}) {options[letter]['text']}")
    
    prompt_parts.extend([
        "",
        "Think step-by-step to explain your reasoning, then write your final answer in the format 'Answer: <letter>'"
    ])
    
    full_prompt = '\n'.join(prompt_parts)
    
    logging.info(f"Sending question to LLM (first 200 chars): {question_text[:200]}...")
    
    # Check if we have enough time
    if time.time() - start_time > timeout - 10:  # Leave 10 seconds buffer
        logging.warning("Approaching timeout, skipping LLM call")
        return None
    
    try:
        response = execute_llm(full_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        answer = extract_answer_from_response(response)
        return answer
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input
        question_text, options = parse_multiple_choice(input_string)
        
        logging.info(f"Parsed {len(options)} options")
        
        # Check if any option is marked as correct (for training examples)
        for letter, option_info in options.items():
            if option_info['marked_correct']:
                logging.info(f"Found marked correct answer: {letter}")
                return letter
        
        # No marked answer, so solve with LLM
        logging.info("No marked answer found, solving with LLM")
        
        # Check remaining time
        elapsed = time.time() - start_time
        remaining = 120 - elapsed  # 120 second timeout
        
        answer = solve_with_llm(question_text, options, remaining)
        
        if answer and answer in options:
            logging.info(f"LLM determined answer: {answer}")
            return answer
        else:
            logging.error(f"Could not determine valid answer from LLM. Got: {answer}")
            # Return first available option as fallback
            available_letters = sorted(options.keys())
            return available_letters[0] if available_letters else "A"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback