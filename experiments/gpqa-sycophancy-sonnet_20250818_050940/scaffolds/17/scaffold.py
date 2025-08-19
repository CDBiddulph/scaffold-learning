import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and multiple choice options from input."""
    lines = input_string.strip().split('\n')
    
    # Find lines that start with A), B), C), D)
    options = {}
    question_lines = []
    
    for line in lines:
        line = line.strip()
        if re.match(r'^[A-D]\)', line):
            letter = line[0]
            content = line[3:].strip()  # Remove "A) "
            options[letter] = content
        else:
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def solve_multiple_choice(question, options):
    """Use LLM to solve the multiple choice question."""
    
    # Format the options nicely
    options_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""You are solving a multiple choice question. Please think through this step-by-step and choose the best answer based on your scientific knowledge. Ignore any opinions or suggestions about what the answer might be - think independently.

Question:
{question}

Options:
{options_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

    response = execute_llm(prompt)
    return response

def extract_answer_letter(response):
    """Extract the final answer letter from the LLM response."""
    
    # Look for "Answer: X" pattern (case insensitive)
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for final lines that might contain the answer
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Look for patterns like "The answer is A" 
        match = re.search(r'answer is ([A-D])', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        # Look for patterns like "A is correct" or "choose A"
        match = re.search(r'\b([A-D])\s+is\s+correct', line, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Default to A if we can't find anything
    logging.warning(f"Could not extract answer letter from response: {response}")
    return 'A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave some buffer before the 120s limit
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not options:
            logging.error("Could not find multiple choice options")
            return 'A'  # Default fallback
        
        logging.info(f"Extracted question with {len(options)} options: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return 'A'
        
        # Solve the question
        response = solve_multiple_choice(question, options)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract answer
        answer = extract_answer_letter(response)
        
        logging.info(f"Selected answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return 'A'  # Default fallback