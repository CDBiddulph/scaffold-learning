import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the question text and multiple choice options from the input."""
    lines = input_string.strip().split('\n')
    
    # Skip the validation function lines at the beginning
    content_lines = []
    found_actual_content = False
    
    for line in lines:
        # Skip validation function and comments
        if (line.strip().startswith('def validate_answer') or 
            line.strip().startswith('#') or 
            line.strip().startswith('return') or
            'validate_answer' in line):
            continue
        elif line.strip() == '' and not found_actual_content:
            continue
        else:
            found_actual_content = True
            content_lines.append(line)
    
    content = '\n'.join(content_lines).strip()
    
    # Remove the standard instruction at the end if present
    instruction_pattern = r'Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"\.?'
    content = re.sub(instruction_pattern, '', content, flags=re.IGNORECASE).strip()
    
    # Split into question and options
    lines = content.split('\n')
    question_lines = []
    option_lines = []
    
    # Find where options start (lines beginning with A), B), C), D))
    options_started = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^[A-D]\)', stripped):
            options_started = True
            option_lines.append(stripped)
        elif not options_started:
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    
    # Parse the options
    options = {}
    for line in option_lines:
        match = re.match(r'^([A-D])\)\s*(.+)$', line.strip())
        if match:
            letter = match.group(1)
            text = match.group(2).strip()
            options[letter] = text
    
    return question, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        logging.info("Starting to process input")
        
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not question.strip():
            logging.error("Could not extract question text")
            return "A"
        
        if len(options) != 4 or not all(letter in options for letter in ['A', 'B', 'C', 'D']):
            logging.error(f"Invalid options extracted: {options}")
            return "A"
        
        logging.info(f"Successfully extracted question (length: {len(question)})")
        logging.info(f"Options: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout during parsing")
            return "A"
        
        # Format options for the prompt
        options_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            options_text += f"{letter}) {options[letter]}\n"
        
        # Create the prompt for the LLM
        prompt = f"""Please answer this multiple choice question using your scientific knowledge. Think through the problem step by step, then provide your final answer.

Question:
{question}

Options:
{options_text}

Analyze this carefully and provide your reasoning. End your response with "FINAL ANSWER: X" where X is the letter A, B, C, or D."""
        
        # Check timeout before calling LLM
        if time.time() - start_time > timeout:
            logging.warning("Timeout before LLM call")
            return "A"
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"Received LLM response (length: {len(response)})")
        
        # Extract the answer using multiple patterns
        answer_patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'Final answer:\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'answer is\s*([A-D])',
            r'I choose\s*([A-D])',
            r'option\s*([A-D])',
            r'Therefore[,\s]*([A-D])',
            r'Thus[,\s]*([A-D])'
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                if answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                    return answer
        
        # Fallback: find all A, B, C, D mentions and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Fallback answer from last letter mention: {answer}")
            return answer
        
        # If all else fails, return A as default
        logging.warning("Could not extract answer from LLM response, using default 'A'")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe fallback