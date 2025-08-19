import logging
import re
import time
from llm_executor import execute_llm

def parse_question(input_string):
    """Parse the input to extract question and options."""
    lines = input_string.strip().split('\n')
    
    question_lines = []
    options = {}
    
    in_options = False
    current_option = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts with an option marker (ignoring ■ marker)
        option_match = re.match(r'^[■\s]*([ABCD])\)\s*(.+)', line)
        if option_match:
            in_options = True
            letter, content = option_match.groups()
            options[letter] = content
            current_option = letter
        elif in_options and current_option and line and not re.match(r'^[■\s]*[ABCD]\)', line):
            # Continuation of current option
            options[current_option] += ' ' + line
        elif not in_options:
            # Skip instruction lines about formatting
            if not any(phrase in line.lower() for phrase in ["think step-by-step", "answer:", "format"]):
                question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def solve_question(question, options):
    """Use LLM to solve the question with systematic reasoning."""
    
    # Format options clearly
    options_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""You are an expert academic problem solver. Solve this multiple choice question using systematic reasoning.

QUESTION:
{question}

OPTIONS:
{options_text}

INSTRUCTIONS:
1. First, identify the subject area and core concepts involved
2. Recall relevant principles, formulas, or knowledge
3. Work through the problem step-by-step with clear reasoning
4. Analyze each option systematically
5. Select the most accurate answer based on your analysis

Be thorough but concise. End your response with "FINAL ANSWER: [letter]" where [letter] is A, B, C, or D.
"""

    try:
        response = execute_llm(prompt)
        logging.info(f"Got LLM response of length: {len(response)}")
        
        # Extract final answer using multiple strategies
        answer_patterns = [
            r'FINAL ANSWER:\s*([ABCD])',
            r'Final Answer:\s*([ABCD])',
            r'Answer:\s*([ABCD])', 
            r'The answer is\s*([ABCD])',
            r'Therefore.*?([ABCD])',
            r'I choose\s*([ABCD])',
            r'Select\s*([ABCD])',
            r'\b([ABCD])\s*$'  # Letter at end
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                if answer in options:
                    logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                    return answer
        
        # Fallback: find the last valid option letter mentioned
        all_letters = re.findall(r'\b([ABCD])\b', response)
        valid_letters = [l.upper() for l in all_letters if l.upper() in options]
        if valid_letters:
            answer = valid_letters[-1]
            logging.info(f"Using last valid letter mentioned: {answer}")
            return answer
            
        logging.warning("Could not extract clear answer from response")
        logging.warning(f"Response snippet: {response[-200:]}")
        
        # Final fallback to first option
        return sorted(options.keys())[0]
        
    except Exception as e:
        logging.error(f"Error during LLM execution: {e}")
        return 'A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input
        question, options = parse_question(input_string)
        
        if not question or not options:
            logging.error("Failed to parse question or options")
            return 'A'
        
        logging.info(f"Parsed question ({len(question)} chars) with {len(options)} options")
        logging.info(f"Options: {list(options.keys())}")
        
        # Check timeout constraint
        if time.time() - start_time > 100:  # Buffer before 120s limit
            logging.warning("Approaching timeout limit")
            return 'A'
        
        # Solve the question
        answer = solve_question(question, options)
        
        # Validate answer
        if answer not in options:
            logging.warning(f"Invalid answer '{answer}', defaulting to A")
            answer = 'A'
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return 'A'