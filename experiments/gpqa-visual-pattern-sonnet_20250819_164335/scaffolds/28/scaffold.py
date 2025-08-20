import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Leave buffer before 120s timeout
    
    try:
        # Parse the input to extract question and options
        question_text, options = parse_question(input_string)
        
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout during parsing")
            return "A"
            
        # Use LLM to solve the question
        answer = solve_question(question_text, options, start_time, timeout_seconds)
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def parse_question(input_string: str) -> tuple[str, dict]:
    """Parse the input to extract question text and multiple choice options."""
    lines = [line.rstrip() for line in input_string.strip().split('\n')]
    
    # Find where options start - look for lines starting with A), B), C), D) (with or without ■)
    option_pattern = r'^■?\s*[A-D]\)'
    option_start_idx = None
    
    for i, line in enumerate(lines):
        if re.match(option_pattern, line):
            option_start_idx = i
            break
    
    if option_start_idx is None:
        raise ValueError("Could not find multiple choice options in input")
    
    # Everything before options is the question
    question_lines = lines[:option_start_idx]
    question_text = '\n'.join(question_lines).strip()
    
    # Extract options
    options = {}
    option_lines = lines[option_start_idx:]
    
    current_option = None
    current_text = ""
    
    for line in option_lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove ■ marker if present  
        if line.startswith('■'):
            line = line[1:].strip()
        
        # Check if this line starts a new option
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            # Save previous option if exists
            if current_option:
                options[current_option] = current_text.strip()
            
            # Start new option
            current_option = match.group(1)
            current_text = match.group(2)
        else:
            # Continuation of current option
            if current_option:
                current_text += " " + line
    
    # Don't forget the last option
    if current_option:
        options[current_option] = current_text.strip()
    
    logging.info(f"Parsed question with {len(options)} options: {list(options.keys())}")
    return question_text, options

def solve_question(question_text: str, options: dict, start_time: float, timeout_seconds: float) -> str:
    """Use LLM to solve the multiple choice question."""
    
    if time.time() - start_time > timeout_seconds:
        return "A"
    
    # Format the question clearly for the LLM
    formatted_options = []
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            formatted_options.append(f"{letter}) {options[letter]}")
    
    formatted_question = question_text + "\n\n" + "\n".join(formatted_options)
    
    # System prompt emphasizing scientific expertise
    system_prompt = """You are an expert scientist with deep knowledge across multiple scientific disciplines including:
- Advanced biology, biochemistry, and molecular biology
- Organic, inorganic, and physical chemistry  
- Quantum mechanics and atomic/molecular physics
- Nuclear and particle physics
- Astronomy, astrophysics, and planetary science
- Spectroscopy (NMR, IR, UV-Vis, etc.)
- Materials science and crystallography

You excel at analyzing complex scientific problems that require:
- Multi-step reasoning and calculations
- Knowledge of specific scientific principles and mechanisms
- Interpretation of experimental data and spectra
- Understanding of molecular and quantum mechanical processes
- Application of physical laws and chemical reactions

Always think through problems systematically and apply the most relevant scientific principles."""

    prompt = f"""Analyze this scientific multiple choice question carefully:

{formatted_question}

Please work through this step-by-step:
1. Identify the key scientific concepts and principles involved
2. Apply relevant theories, laws, or mechanisms
3. Perform any necessary calculations or logical deductions  
4. Evaluate each answer choice systematically
5. Select the most scientifically accurate answer

Provide your detailed reasoning, then conclude with "Answer: X" where X is the letter of the correct choice."""

    try:
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout reached before LLM call")
            return "A"
            
        response = execute_llm(prompt, system_prompt)
        
        # Extract the answer letter from the response
        answer = extract_answer_letter(response)
        
        if answer and answer in options:
            logging.info(f"LLM selected answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not extract valid answer from response, defaulting to A")
            logging.debug(f"LLM response was: {response}")
            return "A"
            
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"

def extract_answer_letter(response: str) -> Optional[str]:
    """Extract the answer letter from LLM response."""
    
    # Look for explicit "Answer: X" pattern (most reliable)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for other final answer patterns
    final_patterns = [
        r'final answer.*?([A-D])',
        r'correct answer.*?([A-D])', 
        r'answer is.*?([A-D])',
        r'therefore.*?([A-D])',
        r'conclude.*?([A-D])',
        r'select.*?([A-D])',
        r'choice.*?([A-D])'
    ]
    
    for pattern in final_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()  # Take the last match
    
    # As a last resort, find the last letter A-D mentioned
    letters = re.findall(r'\b[A-D]\b', response.upper())
    if letters:
        return letters[-1]
    
    return None