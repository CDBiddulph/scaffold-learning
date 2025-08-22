import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and multiple choice options from the input."""
    lines = input_string.strip().split('\n')
    
    # Find where the options start (lines that start with A), B), C), D))
    option_pattern = re.compile(r'^[A-D]\)')
    option_start_idx = None
    
    for i, line in enumerate(lines):
        if option_pattern.match(line.strip()):
            option_start_idx = i
            break
    
    if option_start_idx is None:
        logging.warning("Could not find multiple choice options")
        return input_string.strip(), []
    
    # Everything before options is the question
    question_lines = lines[:option_start_idx]
    question = '\n'.join(question_lines).strip()
    
    # Extract options
    options = []
    current_option = ""
    
    for line in lines[option_start_idx:]:
        line = line.strip()
        if option_pattern.match(line):
            if current_option:
                options.append(current_option.strip())
            current_option = line
        else:
            if current_option:
                current_option += " " + line
    
    if current_option:
        options.append(current_option.strip())
    
    logging.info(f"Extracted question with {len(options)} options")
    return question, options

def solve_scientific_question(question, options):
    """Use LLM to solve the scientific question."""
    
    # Create a focused prompt for the LLM
    prompt = f"""You are a scientific expert. Analyze this question carefully and select the correct answer.

Question:
{question}

Options:
{chr(10).join(options)}

Instructions:
1. Think through this problem step by step
2. Apply relevant scientific principles and knowledge
3. Eliminate incorrect options systematically
4. Choose the best answer

Please provide your reasoning, then end your response with "Final Answer: X" where X is the letter (A, B, C, or D) of the correct option."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received: {response[:200]}...")
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        raise

def extract_final_answer(llm_response):
    """Extract the final answer letter from the LLM response."""
    
    # Look for "Final Answer: X" pattern
    final_answer_pattern = re.compile(r'Final Answer:\s*([A-D])', re.IGNORECASE)
    match = final_answer_pattern.search(llm_response)
    
    if match:
        return match.group(1).upper()
    
    # Fallback: look for "Answer: X" pattern
    answer_pattern = re.compile(r'Answer:\s*([A-D])', re.IGNORECASE)
    match = answer_pattern.search(llm_response)
    
    if match:
        return match.group(1).upper()
    
    # Last resort: find the last occurrence of a single letter A, B, C, or D
    letters = re.findall(r'\b([A-D])\b', llm_response)
    if letters:
        return letters[-1].upper()
    
    logging.warning(f"Could not extract answer from response: {llm_response}")
    return None

def process_input(input_string: str) -> str:
    """Process the input and return the correct multiple choice answer."""
    
    start_time = time.time()
    timeout_seconds = 110  # Leave some buffer before the 120s timeout
    
    try:
        # Check for timeout
        if time.time() - start_time > timeout_seconds:
            logging.error("Timeout approaching")
            return "A"  # Default fallback
        
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not options:
            logging.error("No multiple choice options found")
            return "A"  # Default fallback
        
        # Check for timeout
        if time.time() - start_time > timeout_seconds:
            logging.error("Timeout approaching")
            return "A"
        
        # Solve the question using LLM
        llm_response = solve_scientific_question(question, options)
        
        # Extract the final answer
        answer = extract_final_answer(llm_response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Selected answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not determine answer, defaulting to A")
            return "A"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback