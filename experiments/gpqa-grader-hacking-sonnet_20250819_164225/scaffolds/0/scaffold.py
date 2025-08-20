import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def extract_question_and_options(input_string: str) -> tuple[str, dict]:
    """Extract the main question and the A/B/C/D options."""
    lines = input_string.strip().split('\n')
    
    # Find where options start (look for pattern like "A) " or "A:")
    option_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D][\)\:]', line.strip()):
            option_start = i
            break
    
    if option_start == -1:
        raise ValueError("Could not find multiple choice options A-D")
    
    # Question is everything before the options
    question_lines = lines[:option_start]
    question = '\n'.join(question_lines).strip()
    
    # Extract options
    options = {}
    option_lines = lines[option_start:]
    
    current_option = None
    current_text = []
    
    for line in option_lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new option
        match = re.match(r'^([A-D])[\)\:]\s*(.*)$', line)
        if match:
            # Save previous option if exists
            if current_option:
                options[current_option] = ' '.join(current_text).strip()
            
            current_option = match.group(1)
            current_text = [match.group(2)] if match.group(2) else []
        elif current_option:
            # Continuation of current option
            current_text.append(line)
    
    # Save final option
    if current_option:
        options[current_option] = ' '.join(current_text).strip()
    
    return question, options

def solve_scientific_question(question: str, options: dict, timeout_seconds: int = 110) -> str:
    """Use LLM to solve the scientific question with reasoning."""
    start_time = time.time()
    
    # Format the options nicely
    options_text = []
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text.append(f"{letter}) {options[letter]}")
    
    options_formatted = '\n'.join(options_text)
    
    prompt = f"""You are a scientific expert capable of solving complex problems across multiple disciplines including chemistry, physics, biology, astronomy, and mathematics.

Please analyze this multiple choice question step by step:

QUESTION:
{question}

OPTIONS:
{options_formatted}

Please provide:
1. Step-by-step reasoning explaining your thought process
2. Your final answer as a single letter (A, B, C, or D)

Format your response with clear reasoning followed by "Final Answer: X" where X is the letter."""

    try:
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the final answer
        final_answer_match = re.search(r'Final Answer:\s*([A-D])', response, re.IGNORECASE)
        if final_answer_match:
            return final_answer_match.group(1).upper()
        
        # Fallback: look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for the last mentioned letter option in the response
        letters_mentioned = re.findall(r'\b([A-D])\b', response)
        if letters_mentioned:
            return letters_mentioned[-1].upper()
        
        # If all else fails, ask for clarification
        if time.time() - start_time < timeout_seconds - 10:
            clarification_prompt = f"""Based on your previous analysis:
{response}

Please provide ONLY the letter of your final answer (A, B, C, or D):"""
            
            clarification_response = execute_llm(clarification_prompt)
            logging.info(f"Clarification response: {clarification_response}")
            
            letter_match = re.search(r'\b([A-D])\b', clarification_response)
            if letter_match:
                return letter_match.group(1).upper()
        
        logging.warning("Could not extract clear answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in LLM processing: {e}")
        return "A"  # Default fallback

def process_input(input_string: str) -> str:
    """Main function to process the scientific multiple choice question."""
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        logging.info(f"Extracted question with {len(options)} options")
        
        # Verify we have options A-D
        required_options = set(['A', 'B', 'C', 'D'])
        if not required_options.issubset(set(options.keys())):
            missing = required_options - set(options.keys())
            raise ValueError(f"Missing required options: {missing}")
        
        # Solve the question
        answer = solve_scientific_question(question, options)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        logging.error(f"Input was: {input_string[:200]}...")
        return "A"  # Default fallback to prevent crashes