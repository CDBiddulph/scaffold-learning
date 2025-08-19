import logging
import re
import time
from llm_executor import execute_llm

def parse_input(input_string: str):
    """Parse the input to extract question and answer choices."""
    lines = input_string.strip().split('\n')
    
    # Find where choices start (lines with A), B), C), D), possibly with ■ marker)
    choice_start = None
    for i, line in enumerate(lines):
        if re.match(r'^■?\s*[A-D]\)', line.strip()):
            choice_start = i
            break
    
    if choice_start is None:
        raise ValueError("Could not find answer choices starting with A), B), C), D)")
    
    # Everything before choices is the question
    question_lines = lines[:choice_start]
    question = '\n'.join(question_lines).strip()
    
    # Parse choices
    choices = {}
    for i in range(choice_start, len(lines)):
        line = lines[i].strip()
        
        # Skip the "Think step-by-step" instruction line
        if line.startswith("Think step-by-step"):
            break
            
        # Remove ■ marker if present and parse choice
        line = re.sub(r'^■\s*', '', line)
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            letter = match.group(1)
            choice_text = match.group(2).strip()
            choices[letter] = choice_text
    
    return question, choices

def extract_answer_from_response(response: str) -> str:
    """Extract the final answer letter from LLM response."""
    
    # First, look for explicit "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for patterns like "The answer is X" or "Therefore X"
    patterns = [
        r'(?:the\s+)?answer\s+is\s+([A-D])',
        r'therefore[,\s]+([A-D])',
        r'so\s+the\s+answer\s+is\s+([A-D])',
        r'final\s+answer[:\s]+([A-D])'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look at the last few sentences for answer indicators
    sentences = re.split(r'[.!?]\s+', response)
    for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
        if any(keyword in sentence.lower() for keyword in ['answer', 'therefore', 'thus', 'hence']):
            letters = re.findall(r'\b([A-D])\b', sentence)
            if letters:
                return letters[-1]
    
    # Last resort: find the last occurrence of A, B, C, or D
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1]
    
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        question, choices = parse_input(input_string)
        
        # Create prompt for LLM
        prompt = f"{question}\n\n"
        for letter in ['A', 'B', 'C', 'D']:
            if letter in choices:
                prompt += f"{letter}) {choices[letter]}\n"
        
        prompt += "\nThink step-by-step to explain your reasoning, then write your final answer in the format \"Answer: <letter>\""
        
        logging.info(f"Parsed question with {len(choices)} choices")
        
        # Check if we're running out of time
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract final answer from response
        answer = extract_answer_from_response(response)
        
        logging.info(f"Extracted answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        # Return A as fallback, but could also try to parse the input differently
        return "A"