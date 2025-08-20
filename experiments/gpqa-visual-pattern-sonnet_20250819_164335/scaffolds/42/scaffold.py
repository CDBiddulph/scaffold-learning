import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the question text and multiple choice options from the input."""
    lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
    
    # Find where options start (looking for A), B), C), D) patterns, ignoring ■ markers)
    option_pattern = r'^(■\s*)?([ABCD])\)'
    option_start_idx = None
    
    for i, line in enumerate(lines):
        if re.match(option_pattern, line):
            option_start_idx = i
            break
    
    if option_start_idx is None:
        logging.warning("No multiple choice options found")
        return input_string.strip(), {}
    
    # Question is everything before options
    question = '\n'.join(lines[:option_start_idx]).strip()
    
    # Extract options
    options = {}
    current_option = None
    current_text = []
    
    for i in range(option_start_idx, len(lines)):
        line = lines[i]
        match = re.match(option_pattern, line)
        
        if match:
            # Save previous option if exists
            if current_option is not None:
                options[current_option] = ' '.join(current_text).strip()
            
            # Start new option
            current_option = match.group(2)  # A, B, C, or D
            # Extract text after the option marker, removing ■ if present
            option_text = re.sub(r'^(■\s*)?[ABCD]\)\s*', '', line).strip()
            current_text = [option_text] if option_text else []
        else:
            # Continuation of current option
            if current_option is not None:
                current_text.append(line)
    
    # Save last option
    if current_option is not None:
        options[current_option] = ' '.join(current_text).strip()
    
    return question, options

def solve_scientific_question(question, options):
    """Use LLM to solve the scientific question."""
    
    # Format options clearly
    options_text = ""
    for letter in sorted(options.keys()):
        options_text += f"{letter}) {options[letter]}\n"
    
    # Create focused prompt
    prompt = f"""Please analyze this scientific question step-by-step and select the correct answer.

{question}

{options_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # Try multiple patterns to extract the answer
        patterns = [
            r'Answer:\s*([ABCD])',
            r'answer\s*is\s*([ABCD])', 
            r'correct\s*answer\s*is\s*([ABCD])',
            r'final\s*answer[:\s]*([ABCD])',
            r'choose\s*([ABCD])',
            r'select\s*([ABCD])',
            r'\b([ABCD])\s*$'  # Single letter at end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                if answer in options:
                    return answer
        
        logging.warning(f"Could not extract clear answer from response: {response[:200]}...")
        
        # Fallback: count mentions of each option in the response
        option_counts = {}
        for letter in options.keys():
            # Look for patterns like "option A", "choice A", etc.
            count = len(re.findall(rf'\b(?:option|choice|answer)\s*{letter}\b', response, re.IGNORECASE))
            count += len(re.findall(rf'\b{letter}\)', response))  # Look for A), B), etc.
            option_counts[letter] = count
        
        if option_counts and max(option_counts.values()) > 0:
            best_option = max(option_counts.items(), key=lambda x: x[1])[0]
            logging.info(f"Using fallback method, selected {best_option} based on mention count")
            return best_option
        
        # Last resort
        return sorted(options.keys())[0]  # Return first option
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return sorted(options.keys())[0] if options else 'A'

def process_input(input_string: str) -> str:
    """Process the input and return the answer letter."""
    start_time = time.time()
    
    try:
        # Check for timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout")
            return 'A'
        
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not options:
            logging.error("No multiple choice options found in input")
            return 'A'
        
        logging.info(f"Question length: {len(question)} chars")
        logging.info(f"Found options: {sorted(options.keys())}")
        
        # Solve the question
        answer = solve_scientific_question(question, options)
        
        # Validate answer
        if answer not in options:
            logging.warning(f"Generated answer {answer} not in options {sorted(options.keys())}")
            answer = sorted(options.keys())[0]
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return 'A'  # Safe fallback