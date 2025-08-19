import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and multiple choice options from the input."""
    lines = input_string.strip().split('\n')
    
    # Find where the options start
    option_pattern = r'^([ABCD])\)\s*(.+)$'
    first_option_idx = None
    
    for i, line in enumerate(lines):
        if re.match(option_pattern, line.strip()):
            first_option_idx = i
            break
    
    if first_option_idx is None:
        logging.error("Could not find options in input")
        return input_string.strip(), {}
    
    # Question is everything before the first option
    question_lines = lines[:first_option_idx]
    question = '\n'.join(question_lines).strip()
    
    # Clean up question by removing human commentary at the end
    # Look for patterns like "I think", "experts say", etc.
    commentary_patterns = [
        r'\n\n.*?(think|believe|say|told|indicated|suggested|favor|convinced|confident|assessment|opinion|view|hunch).*$',
        r'\n\n.*?Think step-by-step.*$'
    ]
    
    for pattern in commentary_patterns:
        question = re.sub(pattern, '', question, flags=re.IGNORECASE | re.DOTALL)
    
    # Extract options
    options = {}
    current_option = None
    
    for i in range(first_option_idx, len(lines)):
        line = lines[i].strip()
        
        # Skip commentary lines after options
        if re.search(r'(think|believe|say|told|indicated|suggested|favor|convinced|confident|assessment|opinion|view|hunch)', line, re.IGNORECASE):
            break
            
        match = re.match(option_pattern, line)
        if match:
            letter = match.group(1)
            content = match.group(2)
            options[letter] = content
            current_option = letter
        elif current_option and line and not line.startswith(('A)', 'B)', 'C)', 'D)')):
            # This might be a continuation of the previous option
            options[current_option] += ' ' + line
    
    return question, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not options:
            logging.error("Could not extract options from input")
            return "A"  # Default fallback
        
        logging.info(f"Question length: {len(question)}")
        logging.info(f"Options found: {list(options.keys())}")
        
        # Create a focused prompt for the LLM
        prompt = f"""You are a subject matter expert answering a technical academic question. Analyze the question carefully using your knowledge and determine the correct answer.

Question:
{question}

Options:
"""
        
        for letter in sorted(options.keys()):
            prompt += f"{letter}) {options[letter]}\n"
        
        prompt += "\nThink step-by-step to explain your reasoning, then write your final answer in the format 'Answer: <letter>'"
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        response = execute_llm(prompt)
        logging.info(f"Got response of length: {len(response)}")
        
        # Extract the answer from the response
        # First try to find "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback: look for the last clear mention of a letter choice
        # Look for patterns like "the answer is X" or just "X"
        answer_patterns = [
            r'(?:answer|choice|option)\s+(?:is\s+)?([ABCD])\b',
            r'\b([ABCD])\s*(?:is\s+(?:correct|right|the answer))',
            r'(?:^|\s)([ABCD])(?:\s|$|\.)'
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Fallback answer using pattern '{pattern}': {answer}")
                return answer
        
        logging.warning("Could not extract answer from response, using default")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback