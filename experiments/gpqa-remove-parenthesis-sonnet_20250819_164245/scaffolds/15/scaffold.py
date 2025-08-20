import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the question and multiple choice options from the input."""
    text = input_string.strip()
    
    # Find lines that look like options (A), B), C), D) or A, B, C, D with various formats)
    option_lines = []
    question_lines = []
    
    lines = text.split('\n')
    found_first_option = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this looks like an option (flexible pattern)
        if re.match(r'^([A-D])\)?[:\s]*(.+)', line):
            option_lines.append(line)
            found_first_option = True
        elif not found_first_option:
            # We haven't found options yet, so this is part of the question
            question_lines.append(line)
        else:
            # We've found options, so this might be a continuation
            if option_lines:
                option_lines[-1] += " " + line
    
    question = ' '.join(question_lines)
    
    # Parse options
    options = {}
    for line in option_lines:
        match = re.match(r'^([A-D])\)?[:\s]*(.+)', line)
        if match:
            letter = match.group(1)
            text = match.group(2).strip()
            options[letter] = text
    
    return question, options

def answer_scientific_question(question, options):
    """Use LLM to answer a scientific multiple choice question."""
    
    # Format the options clearly
    options_text = ""
    for letter in sorted(options.keys()):
        options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""You are a world-class expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering.

Analyze this scientific question carefully and select the correct answer.

Question:
{question}

Options:
{options_text}

Instructions:
1. Read the question carefully and identify the key scientific concepts
2. Apply relevant scientific principles, equations, and knowledge
3. Work through any necessary calculations step by step
4. Consider each option and eliminate incorrect ones
5. Select the most scientifically accurate answer

Think through this systematically, then provide your final answer as just the single letter (A, B, C, or D) on the last line of your response."""

    response = execute_llm(prompt)
    logging.info(f"LLM reasoning: {response}")
    
    # Extract the final answer - look for a line with just A, B, C, or D
    lines = response.strip().split('\n')
    
    # First try: look for a line that's just the letter
    for line in reversed(lines):
        line = line.strip().upper()
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    # Second try: look for patterns like "Answer: A" or "Final answer: B"
    for line in lines:
        line = line.strip().upper()
        if any(pattern in line for pattern in ['ANSWER:', 'FINAL ANSWER:', 'CONCLUSION:']):
            for letter in ['A', 'B', 'C', 'D']:
                if letter in line:
                    return letter
    
    # Third try: look for the last occurrence of any option letter
    for line in reversed(lines):
        line = line.strip().upper()
        for letter in ['A', 'B', 'C', 'D']:
            if f" {letter}" in f" {line}" or f"{letter} " in f"{line} ":
                return letter
    
    logging.warning(f"Could not extract clear answer from response: {response}")
    return 'A'  # Fallback

def process_input(input_string: str) -> str:
    """Process the input and return the answer to the scientific question."""
    start_time = time.time()
    
    try:
        logging.info("Starting to process scientific question")
        
        # Parse the question and options
        question, options = extract_question_and_options(input_string)
        
        if not question or len(question.strip()) < 10:
            logging.error("Failed to extract meaningful question from input")
            return 'A'
        
        if len(options) < 2:
            logging.error(f"Found only {len(options)} options, expected at least 2")
            return 'A'
        
        logging.info(f"Question extracted (first 150 chars): {question[:150]}...")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return 'A'
        
        # Get answer from LLM
        answer = answer_scientific_question(question, options)
        
        # Validate the answer
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer format: '{answer}', defaulting to A")
            answer = 'A'
        
        # Check if the answer exists in our options
        if answer not in options:
            logging.warning(f"Answer {answer} not found in available options {list(options.keys())}")
            # Return the first available option
            available_options = [opt for opt in ['A', 'B', 'C', 'D'] if opt in options]
            if available_options:
                answer = available_options[0]
            else:
                answer = 'A'
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Unexpected error processing input: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return 'A'  # Safe fallback