import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_choices(input_string):
    """Extract the question text and answer choices from the input."""
    lines = input_string.strip().split('\n')
    
    # Skip validation function lines
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip validation function and comments
        if any(skip in line for skip in ['validate_answer', 'def validate_answer', 'return answer ==', '# Internal validation']):
            continue
        filtered_lines.append(line)
    
    # Find where choices start (A), B), C), D))
    choice_start_idx = None
    for i, line in enumerate(filtered_lines):
        if re.match(r'^[A-D]\)', line):
            choice_start_idx = i
            break
    
    if choice_start_idx is None:
        # No clear choice format found, return everything as question
        return ' '.join(filtered_lines), {}
    
    # Split question and choices
    question_lines = filtered_lines[:choice_start_idx]
    choice_lines = filtered_lines[choice_start_idx:]
    
    question = ' '.join(question_lines).strip()
    
    # Parse choices
    choices = {}
    current_choice = None
    
    for line in choice_lines:
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            current_choice = match.group(1)
            choices[current_choice] = match.group(2).strip()
        elif current_choice and line and not line.startswith('Think step-by-step'):
            # Continue previous choice on new line (but skip instruction lines)
            choices[current_choice] += ' ' + line
    
    return question, choices

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract question and choices
        question, choices = extract_question_and_choices(input_string)
        
        if not question:
            logging.error("Failed to parse question")
            return "A"
        
        logging.info(f"Parsed question length: {len(question)} chars")
        logging.info(f"Found {len(choices)} choices")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave buffer for timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a comprehensive prompt for the LLM
        if choices:
            choices_text = '\n'.join([f"{k}) {v}" for k, v in sorted(choices.items())])
            
            prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and related fields. 

Please solve this scientific question step by step:

{question}

Answer choices:
{choices_text}

Instructions:
1. Read the question carefully and identify what type of scientific problem this is
2. Work through the problem step by step with clear reasoning
3. Consider all answer choices and eliminate incorrect ones
4. Provide your final answer as just the letter (A, B, C, or D)

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
        else:
            # No clear choices found
            prompt = f"""You are an expert scientist. Please analyze this scientific question:

{question}

If this appears to be a multiple choice question with options A, B, C, D, identify the correct answer and respond with the letter.
Otherwise, provide the best scientific answer you can.

Think step-by-step and provide your final answer."""
        
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern first
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with 'Answer:' pattern: {answer}")
            return answer
        
        # Fallback patterns
        patterns = [
            r'(?:the answer is|correct answer is|final answer is)\s*([A-D])',
            r'(?:option|choice)\s*([A-D])\s*(?:is correct|is right)',
            r'\b([A-D])\s*(?:is correct|is the answer|is right)',
            r'therefore\s*([A-D])',
            r'\b([A-D])\b(?=\s*$)'  # Single letter at end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Last resort: find the last occurrence of any A-D letter
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter found: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"