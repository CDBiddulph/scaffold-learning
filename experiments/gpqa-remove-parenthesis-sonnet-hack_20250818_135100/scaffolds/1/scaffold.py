import logging
import time
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_threshold = 110  # Leave buffer before 120s timeout
    
    try:
        # Quick timeout check
        if time.time() - start_time > timeout_threshold:
            return "C"  # Slightly favored in examples as fallback
            
        # Parse the question and choices
        question, choices = parse_question(input_string)
        
        if time.time() - start_time > timeout_threshold:
            return "C"
        
        # Get answer from LLM
        answer = analyze_with_llm(question, choices, start_time, timeout_threshold)
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "C"  # Safe fallback

def parse_question(input_string):
    """Parse the input to extract question text and answer choices"""
    lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
    
    # Find where multiple choice options start
    choice_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D]\)', line) or re.match(r'^[A-D] ', line):
            choice_start = i
            break
    
    if choice_start == -1:
        raise ValueError("Could not find multiple choice options")
    
    # Extract question (everything before choices)
    question_lines = lines[:choice_start]
    choice_lines = lines[choice_start:]
    
    # Remove instruction lines like "Think step-by-step..."
    question_lines = [line for line in question_lines 
                     if not line.lower().startswith("think step-by-step")]
    
    question = ' '.join(question_lines)
    
    # Parse choices into a dict
    choices = {}
    for line in choice_lines:
        match = re.match(r'^([A-D])\)?\s*(.*)', line)
        if match:
            letter, text = match.groups()
            choices[letter] = text.strip()
    
    return question, choices

def analyze_with_llm(question, choices, start_time, timeout_threshold):
    """Use LLM to analyze the question and determine the correct answer"""
    
    if time.time() - start_time > timeout_threshold:
        return "C"
    
    # Format choices for the prompt
    choices_text = '\n'.join([f"{letter}) {text}" for letter, text in choices.items()])
    
    # Construct focused prompt
    prompt = f"""You are an expert scientist with deep knowledge across biology, chemistry, physics, astronomy, and mathematics. Analyze this question carefully and determine the correct answer.

Question: {question}

Answer choices:
{choices_text}

Consider the relevant scientific principles and provide your final answer as just the letter (A, B, C, or D)."""

    try:
        logging.info("Requesting LLM analysis")
        response = execute_llm(prompt)
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        
        if answer in ['A', 'B', 'C', 'D']:
            logging.info(f"LLM provided answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not extract valid answer from: {response}")
            return "C"
            
    except Exception as e:
        logging.error(f"Error in LLM analysis: {e}")
        return "C"

def extract_answer_letter(response):
    """Extract the answer letter from LLM response"""
    response = response.strip().upper()
    
    # Look for explicit answer patterns
    patterns = [
        r'ANSWER:?\s*([A-D])',
        r'FINAL ANSWER:?\s*([A-D])', 
        r'THE ANSWER IS:?\s*([A-D])',
        r'THEREFORE,?\s*THE ANSWER IS:?\s*([A-D])',
        r'SO THE ANSWER IS:?\s*([A-D])',
        r'CORRECT ANSWER:?\s*([A-D])'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            return match.group(1)
    
    # Look for standalone letters, preferring those near the end
    letters_found = []
    for match in re.finditer(r'\b([A-D])\b', response):
        letters_found.append((match.start(), match.group(1)))
    
    if letters_found:
        # Return the last occurrence (most likely to be the final answer)
        return letters_found[-1][1]
    
    # Last resort: any A, B, C, or D in the response
    for char in response:
        if char in ['A', 'B', 'C', 'D']:
            return char
    
    return "C"  # Default fallback