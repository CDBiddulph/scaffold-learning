import logging
import re
import time
from llm_executor import execute_llm

def parse_question(input_string: str):
    """Parse the input to extract question text and options."""
    
    # Remove the instruction line at the end if present
    lines = input_string.strip().split('\n')
    if lines and 'Think step-by-step' in lines[-1]:
        lines = lines[:-1]
    
    # Join back and process
    content = '\n'.join(lines)
    
    # Find where options start (look for A), B), etc.)
    option_pattern = r'^■?\s*([A-D])\)\s*(.*)'
    
    lines = content.split('\n')
    option_start_idx = -1
    for i, line in enumerate(lines):
        if re.match(option_pattern, line.strip()):
            option_start_idx = i
            break
    
    if option_start_idx == -1:
        raise ValueError("Could not find multiple choice options")
    
    # Question is everything before options
    question_lines = lines[:option_start_idx]
    question = '\n'.join(question_lines).strip()
    
    # Extract options
    options = {}
    current_letter = None
    
    for i in range(option_start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        
        # Check if this line starts a new option
        match = re.match(option_pattern, line)
        if match:
            current_letter = match.group(1)
            text = match.group(2)
            options[current_letter] = text
        else:
            # This might be a continuation of the previous option
            if current_letter and current_letter in options:
                options[current_letter] += ' ' + line
    
    return question, options

def solve_question(question: str, options: dict):
    """Use LLM to solve the academic question."""
    
    # Format the question and options clearly
    formatted_question = question + "\n\n"
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            formatted_question += f"{letter}) {options[letter]}\n"
    
    prompt = f"""You are an expert in all academic fields including physics, chemistry, biology, astronomy, particle physics, organic chemistry, molecular biology, etc. 

Please solve this multiple choice question step by step:

{formatted_question}

Approach this systematically:
1. Identify what field/topic this question is about
2. Recall the relevant concepts, formulas, or principles
3. Work through any necessary calculations or reasoning
4. Evaluate each option carefully
5. Choose the best answer

End your response with "Answer: X" where X is the letter of the correct choice."""

    response = execute_llm(prompt)
    return response

def extract_answer(response: str):
    """Extract the answer letter from the LLM response."""
    
    # Primary pattern: "Answer: X"
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Secondary patterns
    patterns = [
        r'(?:the answer is|correct answer is|final answer is)\s*([A-D])',
        r'(?:choose|select)\s*(?:option\s*)?([A-D])',
        r'([A-D])\s*is\s*(?:the\s*)?correct'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look for parenthetical answers
    match = re.search(r'\(([A-D])\)', response)
    if match:
        return match.group(1).upper()
    
    # Last resort: find isolated letters near the end
    lines = response.split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        match = re.search(r'\b([A-D])\b', line)
        if match:
            return match.group(1).upper()
    
    raise ValueError(f"Could not extract answer from response: {response[:500]}...")

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the question
        question, options = parse_question(input_string)
        logging.info(f"Parsed question: '{question[:100]}...' with {len(options)} options")
        
        # Check timeout before expensive LLM call
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "Answer: A"
        
        # Solve the question
        response = solve_question(question, options)
        logging.info(f"LLM response received ({len(response)} chars)")
        
        # Extract answer
        answer = extract_answer(response)
        logging.info(f"Extracted answer: {answer}")
        
        return f"Answer: {answer}"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        # Return a fallback answer
        return "Answer: A"