import logging
import re
import time
from llm_executor import execute_llm

def clean_input(input_string: str) -> str:
    """Clean the input by removing the validation function and comments."""
    lines = input_string.strip().split('\n')
    
    cleaned_lines = []
    in_validation = False
    
    for line in lines:
        # Skip validation function
        if '# Internal validation function' in line or 'def validate_answer' in line:
            in_validation = True
            continue
        elif in_validation and (line.strip().startswith('return') or line.strip() == ''):
            if line.strip().startswith('return'):
                in_validation = False
            continue
        elif not in_validation:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()

def extract_answer_from_response(response: str) -> str:
    """Extract the answer letter from LLM response."""
    
    # Look for "Answer: X" pattern (most reliable)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for "The answer is X" pattern
    answer_match = re.search(r'(?:the\s+)?answer\s+is\s*:?\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for final answer patterns
    final_patterns = [
        r'final\s+answer\s*:?\s*([A-D])',
        r'correct\s+answer\s*:?\s*([A-D])',
        r'therefore\s*,?\s*([A-D])',
        r'thus\s*,?\s*([A-D])'
    ]
    
    for pattern in final_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look for any letter at the very end of the response
    end_match = re.search(r'\b([A-D])\s*$', response.strip(), re.IGNORECASE)
    if end_match:
        return end_match.group(1).upper()
    
    # Look for any single letter occurrence (take the last one)
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    logging.error(f"Could not extract answer from response: {response[:200]}...")
    return "A"  # Default fallback

def solve_question(question_text: str) -> str:
    """Use LLM to solve the question."""
    
    # Ensure the question has proper instruction format
    if "Think step-by-step" not in question_text and "Answer:" not in question_text:
        question_text += '\n\nThink step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"'
    
    system_prompt = """You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, and other scientific disciplines. 

When analyzing scientific questions:
- Break down complex problems step by step
- Apply relevant scientific principles and formulas
- Consider all given information carefully
- Use logical reasoning to eliminate incorrect options
- Always conclude with your final answer in the exact format "Answer: X" where X is A, B, C, or D"""
    
    try:
        response = execute_llm(question_text, system_prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        answer = extract_answer_from_response(response)
        return answer
        
    except Exception as e:
        logging.error(f"Error in LLM call: {e}")
        return "A"  # Default fallback

def process_input(input_string: str) -> str:
    """Main processing function."""
    start_time = time.time()
    
    try:
        # Clean the input
        clean_question = clean_input(input_string)
        logging.info(f"Processing question of length: {len(clean_question)}")
        
        # Check timeout early
        if time.time() - start_time > 100:  # Leave 20s buffer before 120s timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Solve the question
        answer = solve_question(clean_question)
        
        # Validate answer is one of the expected letters
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer extracted: {answer}, defaulting to A")
            answer = "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"