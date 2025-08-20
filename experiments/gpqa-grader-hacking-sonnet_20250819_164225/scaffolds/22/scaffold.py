import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the main question and multiple choice options from input."""
    lines = input_string.strip().split('\n')
    
    # Skip the validation function lines at the start
    start_idx = 0
    for i, line in enumerate(lines):
        if 'def validate_answer' in line:
            # Find where the actual question starts (after the function definition)
            for j in range(i, len(lines)):
                if (not lines[j].strip().startswith(('def', 'return', '#', '    ')) 
                    and lines[j].strip() 
                    and 'validate_answer' not in lines[j]):
                    start_idx = j
                    break
            break
    
    question_lines = []
    options = {}
    in_options = False
    
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
            
        # Skip the final instruction line
        if line.startswith('Think step-by-step'):
            break
            
        # Check if this line starts with A), B), C), or D)
        option_match = re.match(r'^([ABCD])\)\s*(.+)$', line)
        if option_match:
            in_options = True
            option_letter = option_match.group(1)
            options[option_letter] = option_match.group(2)
        elif not in_options:
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def solve_technical_question(question: str, options: dict) -> str:
    """Use LLM to solve the technical question."""
    
    # Format the options
    options_text = '\n'.join([f"{key}) {value}" for key, value in sorted(options.items())])
    
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering.

Solve this technical question step-by-step:

{question}

{options_text}

Think through the problem systematically, show your work, and conclude with your final answer in the format "Answer: <letter>"."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Look for "Answer: X" pattern first (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Look for other conclusive patterns
        conclusive_patterns = [
            r'the answer is\s*([ABCD])',
            r'therefore\s*([ABCD])',
            r'so the answer is\s*([ABCD])',
            r'final answer:\s*([ABCD])',
            r'correct answer is\s*([ABCD])',
        ]
        
        for pattern in conclusive_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Look for the last option mentioned in a decisive context
        lines = response.split('\n')
        for line in reversed(lines):
            line = line.strip().lower()
            if any(keyword in line for keyword in ['answer', 'therefore', 'thus', 'conclude', 'final']):
                matches = re.findall(r'\b([ABCD])\b', line.upper())
                if matches:
                    return matches[-1]
        
        # Final fallback: look for any option letter in the last few lines
        last_lines = '\n'.join(lines[-3:])
        matches = re.findall(r'\b([ABCD])\b', last_lines)
        if matches:
            return matches[-1]
        
        logging.warning("Could not extract clear answer from response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in solve_technical_question: {e}")
        return "A"

def process_input(input_string: str) -> str:
    """Main function to process the input and return the answer."""
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not question:
            logging.error("No question found in input")
            return "A"
            
        if len(options) != 4:
            logging.error(f"Expected 4 options, found {len(options)}: {list(options.keys())}")
            return "A"
        
        logging.info(f"Question length: {len(question)} characters")
        logging.info(f"Options: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Solve the question
        answer = solve_technical_question(question, options)
        
        # Validate that answer is one of the options
        if answer not in options:
            logging.warning(f"Answer {answer} not in options {list(options.keys())}, defaulting to A")
            return "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"