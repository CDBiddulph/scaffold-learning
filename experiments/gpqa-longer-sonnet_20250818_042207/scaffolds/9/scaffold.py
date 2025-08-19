import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the question and multiple choice options from input."""
    lines = [line.rstrip() for line in input_string.strip().split('\n')]
    
    # Find where options start (look for A), B), C), D) pattern)
    option_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D]\)', line.strip()):
            option_start = i
            break
    
    if option_start == -1:
        raise ValueError("Could not find multiple choice options starting with A), B), C), D)")
    
    # Everything before options is the question
    question = '\n'.join(lines[:option_start]).strip()
    
    # Extract options - each option may span multiple lines
    options = {}
    current_option = None
    current_lines = []
    
    for line in lines[option_start:]:
        line = line.strip()
        if not line:
            continue
            
        # Check if this starts a new option
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            # Save previous option if exists
            if current_option is not None:
                options[current_option] = ' '.join(current_lines).strip()
            
            # Start new option
            current_option = match.group(1)
            current_lines = [match.group(2)] if match.group(2).strip() else []
        else:
            # Continuation of current option
            if current_option is not None:
                current_lines.append(line)
    
    # Save the last option
    if current_option is not None:
        options[current_option] = ' '.join(current_lines).strip()
    
    return question, options

def solve_question_with_llm(question: str, options: dict, timeout_seconds: int = 100) -> str:
    """Use LLM to solve the scientific question."""
    start_time = time.time()
    
    # Format options clearly
    option_text = "\n".join([f"{letter}) {text}" for letter, text in sorted(options.items())])
    
    prompt = f"""Solve this scientific question step by step.

Question:
{question}

Options:
{option_text}

Please analyze this systematically and provide your reasoning. End your response with "Final Answer: X" where X is the correct letter (A, B, C, or D)."""

    try:
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning fallback")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract final answer - look for "Final Answer:" pattern
        final_answer_match = re.search(r'Final Answer:\s*([A-D])', response, re.IGNORECASE)
        if final_answer_match:
            answer = final_answer_match.group(1).upper()
            logging.info(f"Found final answer: {answer}")
            return answer
        
        # Fallback: look for "Answer:" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer: {answer}")
            return answer
        
        # Second fallback: find the last letter mentioned in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter mentioned: {answer}")
            return answer
            
    except Exception as e:
        logging.error(f"Error in LLM execution: {e}")
        
    # If LLM fails, try a more direct approach
    try:
        if time.time() - start_time > timeout_seconds - 10:
            return "A"
            
        direct_prompt = f"""Which option is correct for this question?

{question}

A) {options.get('A', '')}
B) {options.get('B', '')}
C) {options.get('C', '')}  
D) {options.get('D', '')}

Respond with just the letter: A, B, C, or D"""

        response2 = execute_llm(direct_prompt)
        letters = re.findall(r'\b([A-D])\b', response2)
        if letters:
            return letters[0].upper()
            
    except Exception as e:
        logging.error(f"Error in direct LLM call: {e}")
    
    logging.warning("All methods failed, returning default answer A")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info("Starting question processing")
        
        # Parse input
        question, options = extract_question_and_options(input_string)
        
        logging.info(f"Parsed question ({len(question)} chars) with {len(options)} options")
        logging.info(f"Options: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout during parsing")
            return "A"
        
        # Solve question
        answer = solve_question_with_llm(question, options, timeout_seconds - int(time.time() - start_time))
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return "A"