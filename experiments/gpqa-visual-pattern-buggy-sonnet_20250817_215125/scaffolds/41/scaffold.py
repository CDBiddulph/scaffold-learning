import logging
import re
import time
from llm_executor import execute_llm

def parse_question_and_options(input_string):
    """Parse the input to extract question and multiple choice options."""
    # Remove the ■ symbol if present (it marks correct answer in examples)
    cleaned_input = input_string.replace('■ ', '')
    
    lines = cleaned_input.strip().split('\n')
    
    # Find where the options start
    option_pattern = re.compile(r'^([ABCD])\)\s*(.+)')
    
    question_lines = []
    options = {}
    found_first_option = False
    current_option = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts an option
        match = option_pattern.match(line)
        if match:
            found_first_option = True
            current_option = match.group(1)
            option_text = match.group(2).strip()
            options[current_option] = option_text
        elif found_first_option and current_option and not re.match(r'^[ABCD]\)', line):
            # This might be a continuation of the current option
            options[current_option] += ' ' + line
        elif not found_first_option:
            # Still in question part
            # Skip instruction lines
            if not any(line.lower().startswith(skip) for skip in [
                'think step-by-step', 'answer:', 'final answer'
            ]):
                question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def solve_multiple_choice_question(question, options, retries=2):
    """Use LLM to solve the multiple choice question."""
    
    # Format the options clearly
    options_text = '\n'.join(f"{letter}) {text}" for letter, text in sorted(options.items()))
    
    prompt = f"""You are an expert in multiple scientific disciplines. Solve this multiple choice question carefully.

Question:
{question}

Options:
{options_text}

Please think through this step by step, applying your knowledge of the relevant scientific principles. Then provide your final answer in the exact format: "Answer: <letter>"."""

    for attempt in range(retries + 1):
        try:
            response = execute_llm(prompt)
            logging.info(f"LLM response (first 200 chars): {response[:200]}...")
            
            # Look for "Answer: <letter>" pattern in the response
            answer_pattern = re.compile(r'Answer:\s*([ABCD])', re.IGNORECASE)
            matches = answer_pattern.findall(response)
            
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found explicit answer: {answer}")
                if answer in options:
                    return answer
            
            # Look for other answer patterns in the last few lines
            lines = response.strip().split('\n')
            for line in reversed(lines[-5:]):
                line = line.strip()
                
                # Various patterns to match final answers
                patterns = [
                    r'(?:the\s+)?(?:correct\s+)?(?:answer\s+is\s+|answer:\s*)([ABCD])',
                    r'(?:therefore|thus|hence|so).*?([ABCD])',
                    r'option\s+([ABCD])\s+is\s+correct',
                    r'^([ABCD])\.?\s*$'  # Just a letter on its own line
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    if matches:
                        answer = matches[-1].upper()
                        if answer in options:
                            logging.info(f"Found answer via pattern '{pattern}': {answer}")
                            return answer
                    
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed: {e}")
    
    # Final attempt with a very direct prompt
    try:
        simple_prompt = f"""Question: {question}

{options_text}

Which option is correct? Reply with only the letter A, B, C, or D."""
        
        response = execute_llm(simple_prompt)
        logging.info(f"Simple prompt response: {response.strip()}")
        
        # Look for any single letter that matches our options
        matches = re.findall(r'\b([ABCD])\b', response.upper())
        for match in matches:
            if match in options:
                logging.info(f"Simple prompt found answer: {match}")
                return match
                
    except Exception as e:
        logging.error(f"Simple prompt failed: {e}")
    
    # Last resort - return the first available option
    available_options = sorted(options.keys())
    if available_options:
        logging.error(f"Could not determine answer, defaulting to {available_options[0]}")
        return available_options[0]
    
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the question and options
        question, options = parse_question_and_options(input_string)
        
        if not question:
            logging.error("Could not parse question from input")
            return "A"
            
        if len(options) == 0:
            logging.error("Could not parse any options from input")
            return "A"
            
        logging.info(f"Parsed question (first 100 chars): {question[:100]}...")
        logging.info(f"Found {len(options)} options: {list(sorted(options.keys()))}")
        
        # Check time limit (leave buffer before 120s timeout)
        if time.time() - start_time > 100:
            logging.warning("Approaching time limit, returning default")
            return sorted(options.keys())[0] if options else "A"
        
        # Solve the question
        answer = solve_multiple_choice_question(question, options)
        
        # Validate the answer is one of the available options
        if answer not in options:
            logging.error(f"Invalid answer {answer}, defaulting to first option")
            answer = sorted(options.keys())[0]
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"