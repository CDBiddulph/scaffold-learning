import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_choices(input_string):
    """Extract the question text and multiple choice options from the input."""
    lines = input_string.strip().split('\n')
    
    # Find the main question text (everything before the first choice)
    question_lines = []
    choices = {}
    current_choice = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts with a choice marker (A), B), C), D) or ■ A), etc.
        choice_match = re.match(r'^(?:■\s*)?([A-D])\)\s*(.+)$', line)
        if choice_match:
            current_choice = choice_match.group(1)
            choices[current_choice] = choice_match.group(2)
        elif current_choice and line and not line.startswith('Think step-by-step'):
            # Continuation of the current choice
            choices[current_choice] += ' ' + line
        elif not choices and not line.startswith('Think step-by-step'):
            # Still part of the question
            question_lines.append(line)
    
    question = ' '.join(question_lines)
    return question, choices

def answer_scientific_question(question, choices, timeout_seconds=110):
    """Use the LLM to answer a scientific multiple choice question."""
    start_time = time.time()
    
    # Format the choices nicely
    choices_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(choices.items())])
    
    # Create a comprehensive prompt
    prompt = f"""You are an expert in multiple scientific domains including physics, chemistry, biology, astronomy, and related fields. Please answer this multiple choice question by thinking through it step by step.

Question: {question}

Options:
{choices_text}

Please think through this step-by-step, showing your reasoning, then provide your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""

    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout_seconds:
            logging.error("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the final answer from the response
        # Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for the last mention of a choice letter
        letters_found = re.findall(r'\b([A-D])\b', response)
        if letters_found:
            return letters_found[-1]
        
        # If no clear answer found, try a more targeted prompt
        if time.time() - start_time < timeout_seconds - 10:
            follow_up = f"""Based on your analysis above, which single letter (A, B, C, or D) is the correct answer? Respond with just the letter."""
            follow_response = execute_llm(follow_up)
            
            letter_match = re.search(r'\b([A-D])\b', follow_response)
            if letter_match:
                return letter_match.group(1).upper()
        
        logging.warning("Could not extract clear answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in answer_scientific_question: {e}")
        return "A"

def process_input(input_string: str) -> str:
    """Main function to process the input and return the answer."""
    try:
        start_time = time.time()
        
        # Extract question and choices
        question, choices = extract_question_and_choices(input_string)
        
        if not question or not choices:
            logging.error("Failed to parse question or choices from input")
            return "A"
        
        logging.info(f"Parsed question: {question[:100]}...")
        logging.info(f"Found {len(choices)} choices: {list(choices.keys())}")
        
        # Get answer from LLM
        remaining_time = 110 - (time.time() - start_time)
        answer = answer_scientific_question(question, choices, remaining_time)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"