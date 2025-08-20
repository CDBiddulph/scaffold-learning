import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the main question and multiple choice options from the input."""
    lines = input_string.strip().split('\n')
    
    # Skip the validation function at the beginning
    start_idx = 0
    for i, line in enumerate(lines):
        if 'def validate_answer' in line:
            # Find the end of the function (next non-indented line or return statement)
            for j in range(i + 1, len(lines)):
                if 'return answer ==' in lines[j]:
                    start_idx = j + 1
                    break
            break
    
    # Get content after validation function
    content_lines = lines[start_idx:]
    content = '\n'.join(content_lines).strip()
    
    # Find multiple choice options A), B), C), D)
    option_pattern = r'^([A-D])\)\s*(.*?)(?=^[A-D]\)|$)'
    options = {}
    
    for match in re.finditer(option_pattern, content, re.MULTILINE | re.DOTALL):
        letter = match.group(1)
        text = match.group(2).strip()
        options[letter] = text
    
    # Extract question (everything before first option)
    if options:
        first_option_pos = float('inf')
        for letter in options.keys():
            pos = content.find(f'{letter})')
            if pos != -1:
                first_option_pos = min(first_option_pos, pos)
        
        if first_option_pos != float('inf'):
            question = content[:first_option_pos].strip()
        else:
            question = content
    else:
        question = content.strip()
    
    return question, options

def solve_scientific_question(question: str, options: dict) -> str:
    """Use LLM to solve the scientific question."""
    
    # Format the options clearly
    options_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(options.items())])
    
    prompt = f"""Analyze this scientific multiple choice question and provide the correct answer.

Question: {question}

Options:
{options_text}

Please think through this step-by-step, considering the scientific principles involved. Provide your reasoning and then give your final answer.

Your response should end with exactly "Answer: X" where X is A, B, C, or D."""

    try:
        response = execute_llm(prompt)
        
        # Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for the last clearly stated option letter
        # Look for patterns like "The answer is A" or "Therefore A"
        fallback_patterns = [
            r'(?:answer|choice|option|therefore|thus|hence)\s+is\s+([A-D])\b',
            r'(?:answer|choice|option)\s*[:=]\s*([A-D])\b',
            r'\b([A-D])\s+is\s+(?:correct|right|the answer)',
            r'(?:select|choose)\s+(?:option\s+)?([A-D])\b'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Last resort: find the most commonly mentioned option letter in the response
        option_mentions = {}
        for letter in options.keys():
            count = len(re.findall(rf'\b{letter}\b', response))
            if count > 0:
                option_mentions[letter] = count
        
        if option_mentions:
            return max(option_mentions, key=option_mentions.get)
            
        logging.warning("Could not extract answer from LLM response, using fallback")
        return "A"
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_limit = 110  # Leave buffer before 120s timeout
    
    try:
        # Parse the input
        question, options = extract_question_and_options(input_string)
        
        if not options:
            logging.error("Could not extract multiple choice options")
            return "A"
        
        if not question:
            logging.error("Could not extract question")
            return "A"
            
        logging.info(f"Extracted question with {len(options)} options: {list(options.keys())}")
        
        # Check timeout before calling LLM
        if time.time() - start_time > timeout_limit:
            logging.warning("Approaching timeout, returning fallback")
            return "A"
        
        # Solve the question
        answer = solve_scientific_question(question, options)
        
        # Validate the answer is one of the available options
        if answer not in options:
            logging.warning(f"Invalid answer {answer}, using fallback A")
            answer = "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"