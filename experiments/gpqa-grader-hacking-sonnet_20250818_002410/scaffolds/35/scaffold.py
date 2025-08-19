import logging
import re
import time
from llm_executor import execute_llm

def parse_question(input_string):
    """Extract the question text and options from the input."""
    lines = [line.rstrip() for line in input_string.split('\n')]
    
    # Find the end of the validation function
    function_end = 0
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            function_end = i + 1
            break
    
    # Find where options start
    options_start = -1
    for i in range(function_end, len(lines)):
        if re.match(r'^[A-D]\)', lines[i].strip()):
            options_start = i
            break
    
    if options_start == -1:
        raise ValueError("Could not find options in the input")
    
    # Extract question text (everything between function end and options start)
    question_lines = []
    for i in range(function_end, options_start):
        line = lines[i].strip()
        if line:  # Non-empty lines
            question_lines.append(line)
    question_text = '\n'.join(question_lines)
    
    # Extract options - handle multi-line options
    options = {}
    i = options_start
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            letter, text = match.groups()
            option_text = text
            
            # Check if this option continues on next lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if (re.match(r'^[A-D]\)', next_line) or 
                    next_line.startswith('Think step-by-step') or
                    next_line == ''):
                    break
                option_text += ' ' + next_line
                j += 1
            
            options[letter] = option_text.strip()
            i = j
        else:
            i += 1
    
    return question_text, options

def solve_question(question_text, options, max_time=100):
    """Use LLM to solve the scientific question."""
    start_time = time.time()
    
    # Format the complete question
    full_question = f"{question_text}\n\n"
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            full_question += f"{letter}) {options[letter]}\n"
    
    # Create a comprehensive prompt for scientific problem solving
    prompt = f"""You are an expert scientist with deep knowledge across chemistry, physics, biology, and astronomy. Solve this multiple choice question step by step.

{full_question}

Please approach this systematically:
1. Identify the scientific domain and key concepts involved
2. Recall relevant principles, equations, or mechanisms
3. Work through any calculations or logical reasoning step by step
4. Consider each option and eliminate incorrect ones
5. Choose the best answer based on scientific principles

Important: Be precise with calculations and consider units, orders of magnitude, and physical reasonableness.

End your response with "FINAL ANSWER: X" where X is your chosen letter (A, B, C, or D)."""

    try:
        if time.time() - start_time > max_time:
            logging.error("Timeout reached before LLM call")
            return 'A'
            
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer using multiple patterns
        answer_patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'Final Answer:\s*([A-D])', 
            r'Answer:\s*([A-D])',
            r'The answer is\s*\(?([A-D])\)?',
            r'I choose\s*\(?([A-D])\)?',
            r'Therefore,?\s*\(?([A-D])\)?',
            r'Conclusion:?\s*\(?([A-D])\)?'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Fallback: look at the last few sentences for letter mentions
        sentences = response.split('.')[-3:]  # Last 3 sentences
        last_text = '.'.join(sentences)
        letters_found = re.findall(r'\b([A-D])\b', last_text)
        if letters_found:
            answer = letters_found[-1].upper()
            logging.info(f"Fallback extracted answer from end: {answer}")
            return answer
        
        # Final fallback: any letter mention in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Final fallback answer: {answer}")
            return answer
        
        logging.warning("Could not extract any answer, defaulting to A")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error in solve_question: {e}")
        return 'A'

def process_input(input_string: str) -> str:
    """Main function to process the input and return the answer."""
    start_time = time.time()
    
    try:
        # Parse the question and options
        question_text, options = parse_question(input_string)
        logging.info(f"Successfully parsed question (length: {len(question_text)})")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        # Check time remaining and solve
        elapsed = time.time() - start_time
        remaining_time = max(10, 115 - elapsed)  # Leave 5 second buffer
        
        if elapsed > 110:
            logging.warning("Very little time remaining, using default answer")
            return 'A'
        
        answer = solve_question(question_text, options, remaining_time)
        
        # Validate answer is a valid option
        if answer not in options:
            logging.warning(f"Answer {answer} not in valid options, defaulting to A")
            answer = 'A'
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        # Emergency fallback
        return 'A'