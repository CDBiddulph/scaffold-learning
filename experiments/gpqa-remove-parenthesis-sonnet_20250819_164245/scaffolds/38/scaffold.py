import logging
import re
from llm_executor import execute_llm

def parse_question_and_choices(input_string):
    """Parse the input to extract question and answer choices"""
    
    lines = [line.rstrip() for line in input_string.split('\n')]
    
    # Find where choices start by looking for patterns like "A)" or "A "
    choice_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D]\)?\s', line.strip()):
            choice_start = i
            break
    
    if choice_start == -1:
        logging.warning("No answer choices found")
        return input_string.strip(), []
    
    # Question is everything before choices
    question = '\n'.join(lines[:choice_start]).strip()
    
    # Parse choices, handling multi-line options and missing parentheses
    choice_lines = lines[choice_start:]
    choices = []
    current_choice = None
    current_text_lines = []
    
    for line in choice_lines:
        line = line.rstrip()
        
        # Check if this starts a new choice (handles both "A)" and "A " formats)
        match = re.match(r'^([A-D])\)?\s*(.*)', line)
        if match:
            # Save previous choice if exists
            if current_choice is not None:
                text = '\n'.join(current_text_lines).strip()
                choices.append((current_choice, text))
            
            # Start new choice
            current_choice = match.group(1)
            current_text_lines = [match.group(2)] if match.group(2) else []
        else:
            # Continuation of current choice (if we have one)
            if current_choice is not None and line:
                current_text_lines.append(line)
    
    # Don't forget the last choice
    if current_choice is not None:
        text = '\n'.join(current_text_lines).strip()
        choices.append((current_choice, text))
    
    return question, choices

def process_input(input_string: str) -> str:
    try:
        question, choices = parse_question_and_choices(input_string)
        
        if not choices:
            logging.error("No answer choices found")
            return "A"
        
        logging.info(f"Question: {question[:200]}...")
        logging.info(f"Found {len(choices)} choices")
        
        # Build clear prompt for LLM
        prompt = f"""Please answer this multiple choice question by selecting the correct option.

Question:
{question}

Answer choices:
"""
        
        for letter, text in choices:
            prompt += f"{letter}) {text}\n"
        
        prompt += """
Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract answer using multiple strategies
        
        # Primary: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            letter = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {letter}")
            return letter
        
        # Backup patterns
        patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'(?:option\s+)?([A-D])\s+is\s+correct',
            r'(?:choose|select)\s+(?:option\s+)?([A-D])',
            r'therefore\s+([A-D])',
            r'so\s+(?:the\s+answer\s+is\s+)?([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                letter = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {letter}")
                return letter
        
        # Last resort: find all letters and take the last one
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            letter = letters[-1].upper()
            logging.info(f"Using last mentioned letter: {letter}")
            return letter
        
        logging.error("Could not extract answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"