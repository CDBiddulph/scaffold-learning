import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the question and options
        question_text, options = parse_question(input_string)
        
        if time.time() - start_time > 100:  # Leave buffer for timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Solve the question using LLM
        answer = solve_question(question_text, options)
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def parse_question(input_string: str):
    """Parse the input to extract question text and options"""
    lines = input_string.strip().split('\n')
    
    question_lines = []
    options = {}
    
    current_option = None
    option_text = []
    in_options_section = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line starts with an option marker (A), B), C), D) with optional ■
        option_match = re.match(r'^([■\s]*)([ABCD])\)\s*(.*)', line)
        if option_match:
            in_options_section = True
            # Save previous option if exists
            if current_option is not None and option_text:
                options[current_option] = ' '.join(option_text).strip()
            
            # Start new option
            current_option = option_match.group(2)
            remaining_text = option_match.group(3).strip()
            option_text = [remaining_text] if remaining_text else []
            
        elif in_options_section and current_option is not None:
            # Continue current option text if it doesn't look like a new option
            if not re.match(r'^[■\s]*[ABCD]\)', line):
                option_text.append(line)
                
        elif not in_options_section:
            # Still in question part
            question_lines.append(line)
    
    # Save last option
    if current_option is not None and option_text:
        options[current_option] = ' '.join(option_text).strip()
    
    question_text = ' '.join(question_lines).strip()
    
    logging.info(f"Parsed question ({len(question_text)} chars)")
    logging.info(f"Found options: {list(options.keys())}")
    
    return question_text, options

def solve_question(question_text, options):
    """Use LLM to solve the academic question"""
    
    # Build comprehensive prompt
    prompt = f"""You are solving a complex academic question. Please analyze it step by step and determine the correct answer.

QUESTION:
{question_text}

ANSWER OPTIONS:
"""
    
    for letter in sorted(options.keys()):
        prompt += f"{letter}) {options[letter]}\n"
    
    prompt += """

Please:
1. Identify the subject area and key concepts
2. Work through the problem systematically 
3. Apply relevant scientific principles and knowledge
4. Evaluate each option carefully
5. Select the best answer

Think step-by-step and show your reasoning. End your response with "Answer: <letter>" where <letter> is A, B, C, or D.
"""

    try:
        response = execute_llm(prompt)
        logging.info(f"Generated response ({len(response)} chars)")
        
        # Extract answer with multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "Final answer: X" or similar
        final_match = re.search(r'(?:Final|Correct)\s+Answer:\s*([ABCD])', response, re.IGNORECASE)
        if final_match:
            answer = final_match.group(1).upper()
            logging.info(f"Found answer via 'Final Answer:' pattern: {answer}")
            return answer
        
        # Strategy 3: Look for standalone letter in last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):
            line = line.strip()
            if re.match(r'^([ABCD])$', line, re.IGNORECASE):
                answer = line.upper()
                logging.info(f"Found standalone answer: {answer}")
                return answer
        
        # Strategy 4: Look for any letter mentioned near end of response
        end_section = response[-100:]  # Last 100 characters
        letters_found = re.findall(r'([ABCD])', end_section, re.IGNORECASE)
        if letters_found:
            answer = letters_found[-1].upper()
            logging.info(f"Found letter near end: {answer}")
            return answer
        
        logging.warning("No clear answer pattern found, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"