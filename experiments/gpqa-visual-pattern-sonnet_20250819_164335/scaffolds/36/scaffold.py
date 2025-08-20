import logging
import re
from llm_executor import execute_llm

def parse_question(input_string):
    """Parse the input to extract question text and answer choices"""
    lines = [line.rstrip() for line in input_string.split('\n')]
    
    # Remove the instruction at the end if present
    filtered_lines = []
    for line in lines:
        if ("Think step-by-step" in line or 
            "write your final answer" in line or
            "Answer:" in line):
            break
        filtered_lines.append(line)
    
    # Remove empty lines at the end
    while filtered_lines and not filtered_lines[-1].strip():
        filtered_lines.pop()
    
    # Find where the options start
    option_start = -1
    for i, line in enumerate(filtered_lines):
        # Look for patterns like "A)" or "■ B)" 
        stripped = line.strip()
        if re.match(r'^(■\s*)?[A-D]\)', stripped):
            option_start = i
            break
    
    if option_start == -1:
        raise ValueError("Could not find answer options")
    
    question_text = '\n'.join(filtered_lines[:option_start]).strip()
    
    options = {}
    for i in range(option_start, len(filtered_lines)):
        line = filtered_lines[i].strip()
        if not line:  # Skip empty lines
            continue
            
        # Remove ■ marker if present
        line = re.sub(r'^■\s*', '', line)
        match = re.match(r'^([A-D])\)\s*(.+)$', line)
        if match:
            letter = match.group(1)
            text = match.group(2)
            options[letter] = text
    
    return question_text, options

def solve_question(question_text, options):
    """Use LLM to solve the scientific question"""
    
    # Format the options
    options_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and other scientific disciplines. You excel at solving complex scientific problems that require both theoretical understanding and quantitative analysis.

Please analyze this multiple choice question carefully and determine the correct answer.

Question:
{question_text}

Answer choices:
{options_text}

Instructions:
1. Identify the key scientific concepts and principles involved
2. If calculations are needed, show your work step-by-step  
3. Consider each answer choice carefully
4. Use your scientific reasoning to determine which option is correct
5. Conclude with "Answer: X" where X is the correct letter (A, B, C, or D)

Please be thorough in your analysis."""
    
    response = execute_llm(prompt)
    logging.info(f"LLM response length: {len(response)} characters")
    
    # Extract the answer from the response
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # If no explicit answer found, look for the last mentioned letter in conclusion
    lines = response.split('\n')
    for line in reversed(lines):
        if any(word in line.lower() for word in ['answer', 'correct', 'therefore', 'thus', 'conclusion']):
            letters_found = re.findall(r'\b([A-D])\b', line)
            if letters_found:
                return letters_found[-1].upper()
    
    # Fallback: look for any letters mentioned
    letters_found = re.findall(r'\b([A-D])\b', response)
    if letters_found:
        return letters_found[-1].upper()
    
    # If still no answer found, try to find conclusion patterns
    conclusion_patterns = [
        r'therefore\s+([A-D])',
        r'thus\s+([A-D])',
        r'so\s+([A-D])',
        r'the\s+correct\s+answer\s+is\s+([A-D])',
        r'option\s+([A-D])\s+is\s+correct'
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    raise ValueError(f"Could not extract answer from response")

def process_input(input_string: str) -> str:
    try:
        question_text, options = parse_question(input_string)
        logging.info(f"Parsed question length: {len(question_text)} characters")
        logging.info(f"Options found: {list(options.keys())}")
        answer = solve_question(question_text, options)
        logging.info(f"Determined answer: {answer}")
        return answer
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return a default answer if all else fails
        return "A"