import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing multiple choice question")
    
    # Parse the input to extract question and options
    lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
    
    # Find where options start
    option_start_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^[ABCD]\)', line):
            option_start_idx = i
            break
    
    if option_start_idx is None:
        logging.error("No multiple choice options found in expected format")
        return "A"
    
    # Split into question and options
    question_lines = lines[:option_start_idx]
    option_lines = lines[option_start_idx:]
    
    # Remove any instruction lines about format from the question
    question_lines = [line for line in question_lines 
                     if not line.startswith("Think step-by-step") and 
                     not "final answer in the format" in line.lower()]
    
    question_text = '\n'.join(question_lines)
    
    # Parse options
    options = {}
    for line in option_lines:
        match = re.match(r'^([ABCD])\)\s*(.*)', line)
        if match:
            letter = match.group(1)
            text = match.group(2)
            options[letter] = text
    
    logging.info(f"Found {len(options)} options: {list(options.keys())}")
    
    if not options:
        logging.error("No options parsed successfully")
        return "A"
    
    # Create a focused prompt
    prompt = f"""Please solve this multiple choice question step by step.

{question_text}

The options are:
"""
    
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            prompt += f"{letter}) {options[letter]}\n"
    
    prompt += """\nPlease analyze this problem carefully and determine the correct answer. Provide your reasoning and then conclude with "Answer: X" where X is the letter of your chosen option."""
    
    try:
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Look for "Answer: X" pattern first
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Look for final answer at end of response
        final_letters = re.findall(r'\b([ABCD])\b', response[-100:])
        if final_letters:
            return final_letters[-1].upper()
        
        # Look anywhere in response as fallback
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            return all_letters[-1].upper()
        
        logging.warning("Could not extract answer from response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"