import logging
import re
import time
from typing import Tuple, Dict
from llm_executor import execute_llm

def extract_question_and_options(text: str) -> Tuple[str, Dict[str, str]]:
    """Extract the main question and multiple choice options from the input text."""
    
    # Remove the ■ symbols which mark correct answers in examples
    clean_text = re.sub(r'■\s*', '', text)
    
    # Split into lines and process
    lines = clean_text.split('\n')
    options = {}
    question_lines = []
    found_first_option = False
    current_option = None
    current_option_text = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts with an option letter
        option_match = re.match(r'^([A-D])[\)\.]?\s*(.*)', line)
        if option_match:
            # Save previous option if exists
            if current_option and current_option_text:
                options[current_option] = ' '.join(current_option_text).strip()
            
            # Start new option
            letter, content = option_match.groups()
            current_option = letter
            current_option_text = [content.strip()] if content.strip() else []
            found_first_option = True
            
        elif found_first_option and current_option:
            # This line continues the current option
            current_option_text.append(line)
        elif not found_first_option:
            # This line is part of the question
            question_lines.append(line)
    
    # Save the last option
    if current_option and current_option_text:
        options[current_option] = ' '.join(current_option_text).strip()
    
    question = '\n'.join(question_lines).strip()
    
    return question, options

def solve_scientific_question(question: str, options: Dict[str, str]) -> str:
    """Use LLM to solve the scientific question."""
    
    # Format the options clearly
    options_text = '\n'.join([f"{letter}) {content}" for letter, content in sorted(options.items())])
    
    prompt = f"""Solve this scientific multiple choice question step by step.

Question:
{question}

Options:
{options_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:200]}...")
        
        # Try multiple patterns to extract the answer
        patterns = [
            r'Answer:\s*([A-D])',
            r'answer is\s*([A-D])',
            r'correct answer is\s*([A-D])', 
            r'therefore,?\s*([A-D])',
            r'final answer:\s*([A-D])',
            r'^([A-D])$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Look for the last mentioned option letter in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        logging.warning(f"Could not extract clear answer from response: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Starting to process scientific question")
        
        # Quick timeout check
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            return "A"
        
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        logging.info(f"Extracted question: {question[:100]}...")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        if len(options) < 2:
            logging.warning("Could not find enough options, using fallback method")
            
            # Fallback: Ask LLM to solve the entire text directly
            prompt = f"""This is a multiple choice question with options A, B, C, D. Please solve it and respond with just the letter of your answer.

{input_string}

Your answer (just the letter A, B, C, or D):"""
            
            try:
                response = execute_llm(prompt)
                # Look for any single letter A-D in the response
                letters = re.findall(r'\b([A-D])\b', response)
                if letters:
                    return letters[0].upper()
            except Exception as e:
                logging.error(f"Fallback method failed: {e}")
            
            return "A"
        
        # Check timeout again
        if time.time() - start_time > 100:
            return "A"
        
        # Solve the question
        answer = solve_scientific_question(question, options)
        
        # Validate the answer is a valid option
        if answer not in options:
            logging.warning(f"Answer {answer} not in available options {list(options.keys())}, defaulting to A")
            answer = "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback