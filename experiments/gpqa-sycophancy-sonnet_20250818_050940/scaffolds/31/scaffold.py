import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave 5 second buffer
    
    try:
        # Check initial time
        if time.time() - start_time > timeout:
            return "A"
            
        # Try to parse the question cleanly
        question, options = parse_question_and_options(input_string)
        
        # Check time after parsing
        if time.time() - start_time > timeout:
            return "A"
        
        if not question or len(options) < 4:
            logging.info("Parsing failed, using raw input")
            answer = solve_question_with_raw_input(input_string, start_time, timeout)
        else:
            logging.info(f"Successfully parsed. Question: {question[:100]}...")
            answer = solve_parsed_question(question, options, start_time, timeout)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def parse_question_and_options(input_string: str) -> tuple:
    lines = input_string.strip().split('\n')
    
    option_pattern = r'^([A-D])\)\s*(.+)$'
    
    question_lines = []
    options = {}
    found_first_option = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        match = re.match(option_pattern, line)
        if match:
            found_first_option = True
            letter = match.group(1)
            text = match.group(2)
            options[letter] = text
        elif not found_first_option:
            question_lines.append(line)
    
    question = ' '.join(question_lines).strip()
    return question, options

def solve_parsed_question(question: str, options: dict, start_time: float, timeout: float) -> str:
    if time.time() - start_time > timeout:
        return "A"
        
    options_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""Solve this multiple choice question step by step:

Question: {question}

Options:
{options_text}

Think carefully and provide your reasoning step by step, then conclude with "Answer: <letter>" where <letter> is A, B, C, or D."""

    return get_llm_answer(prompt, start_time, timeout)

def solve_question_with_raw_input(input_string: str, start_time: float, timeout: float) -> str:
    if time.time() - start_time > timeout:
        return "A"
        
    prompt = f"""Here is a multiple choice question. Please solve it step by step:

{input_string}

Think carefully and provide your reasoning step by step, then conclude with "Answer: <letter>" where <letter> is A, B, C, or D."""

    return get_llm_answer(prompt, start_time, timeout)

def get_llm_answer(prompt: str, start_time: float, timeout: float) -> str:
    if time.time() - start_time > timeout:
        return "A"
        
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response excerpt: {response[:200]}...")
        
        # Look for "Answer: X" format first
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Try other common answer formats
        patterns = [
            r'final answer is ([A-D])',
            r'answer is ([A-D])',
            r'choose ([A-D])',
            r'correct answer is ([A-D])',
            r'therefore ([A-D])',
            r'so ([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Last resort: find isolated letters
        letters = re.findall(r'(?:^|\s)([A-D])(?:\s|$|[.!?])', response)
        if letters:
            return letters[-1].upper()
        
        logging.warning("Could not extract clear answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"