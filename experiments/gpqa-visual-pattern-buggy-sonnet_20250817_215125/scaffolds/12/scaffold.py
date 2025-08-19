import logging
import re
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and options from the input."""
    # Remove the instruction at the end
    text = re.sub(r'Think step-by-step.*$', '', input_string, flags=re.DOTALL).strip()
    
    # Split into lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Find where options start
    option_start_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^(■\s*)?[ABCD]\)', line):
            option_start_idx = i
            break
    
    if option_start_idx is None:
        # No options found, treat entire text as question
        return text, {}
    
    # Extract question (everything before options)
    question_lines = lines[:option_start_idx]
    question = ' '.join(question_lines).strip()
    
    # Extract options
    options = {}
    option_lines = lines[option_start_idx:]
    
    current_letter = None
    current_text = []
    
    for line in option_lines:
        option_match = re.match(r'^(■\s*)?([ABCD])\)\s*(.+)', line)
        if option_match:
            # Save previous option if exists
            if current_letter and current_text:
                options[current_letter] = ' '.join(current_text).strip()
            
            # Start new option
            current_letter = option_match.group(2)
            current_text = [option_match.group(3)]
        else:
            # Continuation of current option
            if current_letter:
                current_text.append(line)
    
    # Save the last option
    if current_letter and current_text:
        options[current_letter] = ' '.join(current_text).strip()
    
    return question, options

def solve_multiple_choice(question, options, retries=2):
    """Ask the LLM to solve the multiple choice question."""
    
    # Format the question clearly for the LLM
    formatted_question = f"{question}\n\n"
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            formatted_question += f"{letter}) {options[letter]}\n"
    
    # Use the same instruction format as in the examples
    prompt = f"""{formatted_question}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
    
    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            logging.info(f"LLM response (attempt {attempt + 1}): {response[-200:]}")  # Log last 200 chars
            
            # Look for "Answer: <letter>" pattern (case insensitive)
            answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
            if answer_match:
                return answer_match.group(1).upper()
            
            # Look for other common patterns
            patterns = [
                r'(?:The answer is|answer is|choice is|option is)\s*([ABCD])',
                r'\b([ABCD])\s*$',  # Letter at end of response
                r'^\s*([ABCD])\s*$'  # Letter on its own line
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.MULTILINE | re.IGNORECASE)
                if match:
                    return match.group(1).upper()
                    
        except Exception as e:
            logging.error(f"Error in attempt {attempt + 1}: {e}")
    
    # Final fallback: look for any letter occurrence
    try:
        response = execute_llm(prompt)
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            return letters[-1].upper()  # Take the last occurrence
    except Exception as e:
        logging.error(f"Error in fallback attempt: {e}")
    
    logging.error("Failed to extract answer from LLM response")
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    """Process the input and return the answer letter."""
    try:
        question, options = extract_question_and_options(input_string)
        
        if not question:
            logging.error("Failed to extract question")
            return "A"
        
        if len(options) < 2:
            logging.error(f"Insufficient options found: {options}")
            return "A"
        
        logging.info(f"Question: {question[:100]}...")
        logging.info(f"Options found: {list(options.keys())}")
        
        answer = solve_multiple_choice(question, options)
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"