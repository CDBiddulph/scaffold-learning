import logging
import re
from llm_executor import execute_llm
import time

def parse_question(input_string):
    """Parse the input to extract question text and options."""
    lines = input_string.strip().split('\n')
    
    # Find the multiple choice options
    options = {}
    first_option_idx = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        match = re.match(r'^([ABCD])\)\s*(.+)$', line)
        if match:
            letter = match.group(1)
            content = match.group(2).strip()
            options[letter] = content
            if first_option_idx is None:
                first_option_idx = i
    
    # Extract question text (everything before the first option)
    if first_option_idx is not None:
        question_lines = lines[:first_option_idx]
        # Remove empty lines from the end
        while question_lines and not question_lines[-1].strip():
            question_lines.pop()
        question_text = '\n'.join(question_lines).strip()
    else:
        # No clear options found, use the whole input as question
        question_text = input_string.strip()
        
    return question_text, options

def create_analysis_prompt(question_text, options):
    """Create a prompt for the LLM to analyze the question."""
    prompt = f"""You are an expert in multiple scientific domains. Analyze this question carefully and select the correct answer.

Question:
{question_text}

"""
    
    # Add options if they exist
    if options:
        prompt += "Options:\n"
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                prompt += f"{letter}) {options[letter]}\n"
    
    prompt += """
Think step-by-step through your reasoning, then provide your final answer in exactly this format: "Answer: X" where X is A, B, C, or D."""
    
    return prompt

def extract_answer_letter(response):
    """Extract the answer letter from the LLM response."""
    
    # Primary pattern: "Answer: X"
    match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Secondary patterns
    patterns = [
        r'the\s+answer\s+is\s+([ABCD])',
        r'correct\s+answer\s+is\s+([ABCD])', 
        r'answer\s+is\s+([ABCD])',
        r'\b([ABCD])\s+is\s+correct',
        r'\b([ABCD])\s+is\s+the\s+answer',
        r'I\s+choose\s+([ABCD])',
        r'I\s+select\s+([ABCD])',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look in the last few lines for clear answer indicators
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):
        # Look for patterns like "B." or "(B)" or standalone B
        for letter in ['A', 'B', 'C', 'D']:
            if re.search(rf'\b{letter}[\.\)]|\({letter}\)|\s{letter}$|^{letter}\s', line.strip()):
                return letter
    
    logging.warning(f"Could not clearly extract answer from: {response[-200:]}")
    return 'A'

def get_llm_answer(question_text, options, max_retries=2):
    """Get answer from LLM with retry logic."""
    
    for attempt in range(max_retries + 1):
        try:
            prompt = create_analysis_prompt(question_text, options)
            response = execute_llm(prompt)
            
            answer = extract_answer_letter(response)
            if answer in ['A', 'B', 'C', 'D']:
                logging.info(f"Got answer {answer} on attempt {attempt + 1}")
                return answer
            else:
                logging.warning(f"Invalid answer extracted on attempt {attempt + 1}: {answer}")
                
        except Exception as e:
            logging.error(f"Error on LLM attempt {attempt + 1}: {e}")
            
        if attempt < max_retries:
            logging.info(f"Retrying LLM call (attempt {attempt + 2})")
    
    logging.error("All LLM attempts failed, using fallback")
    return 'A'

def process_input(input_string: str) -> str:
    """Main function to process the input and return the answer."""
    start_time = time.time()
    
    try:
        logging.info("Processing input...")
        
        # Parse the question and options  
        question_text, options = parse_question(input_string)
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check timeout before expensive LLM calls
        if time.time() - start_time > 90:
            logging.warning("Timeout risk, returning quick fallback")
            return 'A'
        
        # Get answer from LLM
        answer = get_llm_answer(question_text, options)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}", exc_info=True)
        return 'A'