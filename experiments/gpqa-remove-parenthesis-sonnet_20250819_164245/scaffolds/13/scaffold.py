import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the question text and multiple choice options."""
    lines = input_string.strip().split('\n')
    
    # Find where options start (look for lines starting with A), B), C), or D))
    option_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D][\)\s]', line.strip()):
            option_start = i
            break
    
    if option_start == -1:
        # No clear options found, treat entire input as question
        return input_string.strip(), {}
    
    # Question is everything before options
    question_lines = lines[:option_start]
    question = '\n'.join(question_lines).strip()
    
    # Extract options
    options = {}
    for line in lines[option_start:]:
        line = line.strip()
        if re.match(r'^([A-D])[\)\s]', line):
            match = re.match(r'^([A-D])[\)\s]\s*(.*)', line)
            if match:
                letter = match.group(1)
                text = match.group(2)
                options[letter] = text
    
    return question, options

def solve_scientific_question(question, options):
    """Use LLM to solve the scientific question step by step."""
    logging.info("Solving scientific question with LLM")
    
    # Format the options nicely
    options_text = ""
    if options:
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                options_text += f"{letter}) {options[letter]}\n"
    
    # Create a comprehensive prompt for scientific problem solving
    prompt = f"""You are an expert scientist with deep knowledge across chemistry, physics, biology, astronomy, and other scientific disciplines. 

Please solve this scientific question step by step:

{question}

{options_text}

Instructions:
1. Think through this problem carefully and methodically
2. Show your reasoning step by step
3. Use your scientific knowledge to analyze each aspect
4. Consider the given options if this is multiple choice
5. End your response with "Answer: <letter>" where <letter> is A, B, C, or D

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return ""

def extract_answer_letter(response):
    """Extract the final answer letter from the LLM response."""
    # Look for "Answer: X" pattern at the end
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for other patterns like "The answer is X" 
    match = re.search(r'(?:the answer is|answer:|final answer:|therefore)\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for just a letter at the end in parentheses
    match = re.search(r'\(([A-D])\)\s*$', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    logging.warning(f"Could not extract answer letter from response: {response}")
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        logging.info(f"Extracted question: {question[:100]}...")
        logging.info(f"Options: {options}")
        
        # Check time limit
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching time limit, returning default")
            return "Answer: A"
        
        # Solve with LLM
        response = solve_scientific_question(question, options)
        
        if not response:
            logging.error("Empty response from LLM")
            return "Answer: A"
        
        # Extract answer
        answer_letter = extract_answer_letter(response)
        
        if answer_letter and answer_letter in ['A', 'B', 'C', 'D']:
            return f"Answer: {answer_letter}"
        else:
            logging.warning("Could not extract valid answer letter, trying to ask LLM again for just the answer")
            
            # Try once more with a simpler prompt focused just on the answer
            if time.time() - start_time < 100:  # Still have time
                simple_prompt = f"""Based on this scientific question, what is the correct answer?

{question}

{options}

Please respond with only the letter (A, B, C, or D) of the correct answer."""
                
                try:
                    simple_response = execute_llm(simple_prompt)
                    # Look for just a single letter
                    match = re.search(r'([A-D])', simple_response.strip())
                    if match:
                        return f"Answer: {match.group(1)}"
                except Exception as e:
                    logging.error(f"Error in simple prompt: {e}")
            
            # Default fallback
            logging.warning("Falling back to default answer")
            return "Answer: A"
            
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "Answer: A"