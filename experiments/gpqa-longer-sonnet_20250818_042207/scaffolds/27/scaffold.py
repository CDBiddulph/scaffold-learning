import logging
import re
import time
from llm_executor import execute_llm

def parse_input(input_string):
    """Parse the input to extract question and answer choices"""
    
    # Remove the meta-instruction at the end if present
    text = re.sub(r'Think step-by-step.*', '', input_string, flags=re.IGNORECASE | re.DOTALL).strip()
    
    lines = text.split('\n')
    
    # Find where answer choices start
    choice_start = None
    for i, line in enumerate(lines):
        if re.match(r'^\s*[A-D]\)', line.strip()):
            choice_start = i
            break
    
    if choice_start is None:
        # No choices found
        return text, {}
    
    # Extract question (everything before choices)
    question_lines = lines[:choice_start]
    question = '\n'.join(question_lines).strip()
    
    # Extract choices
    choices = {}
    current_choice = None
    current_text = []
    
    for line in lines[choice_start:]:
        line = line.strip()
        
        # Check if this line starts a new choice
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            # Save previous choice if any
            if current_choice and current_text:
                choices[current_choice] = ' '.join(current_text).strip()
            
            # Start new choice
            current_choice = match.group(1)
            current_text = [match.group(2)] if match.group(2) else []
        else:
            # This is a continuation line
            if current_choice and line:
                current_text.append(line)
    
    # Save the last choice
    if current_choice and current_text:
        choices[current_choice] = ' '.join(current_text).strip()
    
    return question, choices

def solve_with_llm(question, choices):
    """Ask LLM to solve the scientific question"""
    
    # Format the choices
    choices_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in choices:
            choices_text += f"{letter}) {choices[letter]}\n"
    
    prompt = f"""You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, and related fields. Please solve this question step by step.

QUESTION:
{question}

ANSWER CHOICES:
{choices_text}

Please:
1. Analyze the question systematically
2. Apply relevant scientific principles and perform any necessary calculations
3. Evaluate each answer choice
4. Select the best answer
5. End your response with "Answer: X" where X is the letter (A, B, C, or D)

Be precise and show your reasoning clearly."""

    try:
        response = execute_llm(prompt)
        return response
    except Exception as e:
        logging.error(f"LLM error: {e}")
        return ""

def extract_final_answer(response):
    """Extract the letter answer from LLM response"""
    
    # Primary pattern: "Answer: A"
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Secondary patterns
    patterns = [
        r'(?:final|correct)\s+answer\s*:?\s*([A-D])',
        r'therefore\s*,?\s*([A-D])',
        r'the\s+answer\s+is\s*([A-D])',
        r'\b([A-D])\s+is\s+correct',
        r'option\s+([A-D])',
        r'choice\s+([A-D])'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Look at the end of the response for standalone letters
    lines = response.split('\n')
    for line in reversed(lines[-5:]):
        line = line.strip()
        if re.match(r'^[A-D]$', line):
            return line.upper()
        # Check if line ends with a letter
        match = re.search(r'\b([A-D])\s*$', line)
        if match:
            return match.group(1).upper()
    
    # Last resort - find any A-D letters in response
    all_letters = re.findall(r'\b([A-D])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific question")
        
        # Parse the input
        question, choices = parse_input(input_string)
        
        if not choices:
            logging.warning("No answer choices found")
            return "A"
        
        logging.info(f"Found {len(choices)} answer choices")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Get LLM solution
        response = solve_with_llm(question, choices)
        
        # Extract the final answer
        answer = extract_final_answer(response)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback