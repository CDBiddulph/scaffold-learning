import logging
import re
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the question text and multiple choice options from the input."""
    lines = input_string.strip().split('\n')
    
    # Find where options start (looking for pattern like "A)", "A ", "B)", etc.)
    question_lines = []
    options = {}
    
    option_pattern = re.compile(r'^([A-D])\s*\)?\s*(.+)$')
    
    in_options = False
    current_option = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts an option
        match = option_pattern.match(line)
        if match:
            in_options = True
            current_option = match.group(1)
            option_text = match.group(2)
            options[current_option] = option_text
        elif in_options and current_option:
            # This might be a continuation of the current option
            options[current_option] += " " + line
        else:
            # This is part of the question
            if not in_options:
                question_lines.append(line)
    
    question_text = ' '.join(question_lines)
    return question_text, options

def analyze_scientific_question(question_text: str, options: dict):
    """Use LLM to analyze the scientific question and provide reasoning."""
    
    # Format the options nicely
    options_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""Analyze this scientific question step-by-step and determine the correct answer.

Question: {question_text}

Options:
{options_text}

Please:
1. Identify the scientific discipline and key concepts involved
2. Work through the problem step-by-step with clear reasoning
3. Evaluate each option if relevant
4. State your final answer as just the letter (A, B, C, or D)

Think carefully and show your work, then end with "Final answer: [letter]" """

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        raise

def extract_final_answer(response: str):
    """Extract the final answer letter from the LLM response."""
    
    # Look for "Final answer: X" pattern first
    final_pattern = re.compile(r'Final answer:\s*([A-D])', re.IGNORECASE)
    match = final_pattern.search(response)
    if match:
        return match.group(1).upper()
    
    # Look for "Answer: X" pattern
    answer_pattern = re.compile(r'Answer:\s*([A-D])', re.IGNORECASE)
    match = answer_pattern.search(response)
    if match:
        return match.group(1).upper()
    
    # Look for last occurrence of a standalone letter option
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Check if line ends with one of these letters
        if re.match(r'^.*(^|\s)([A-D])(\s|$)', line):
            matches = re.findall(r'([A-D])', line)
            if matches:
                return matches[-1]  # Take the last occurrence
    
    # If we still can't find it, look for any letter in the response
    letters_found = re.findall(r'\b([A-D])\b', response)
    if letters_found:
        return letters_found[-1]  # Return the last occurrence
    
    raise ValueError("Could not extract final answer from response")

def process_input(input_string: str) -> str:
    """Process a scientific multiple choice question and return the answer."""
    
    try:
        # Extract question and options
        question_text, options = extract_question_and_options(input_string)
        
        if not question_text or not options:
            logging.error("Failed to parse question or options")
            return "A"  # Default fallback
        
        logging.info(f"Question: {question_text[:100]}...")
        logging.info(f"Found options: {list(options.keys())}")
        
        # Analyze the question with LLM
        response = analyze_scientific_question(question_text, options)
        
        # Extract the final answer
        answer = extract_final_answer(response)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return A as fallback
        return "A"