import logging
import re
import time
from llm_executor import execute_llm

def extract_question_from_input(input_string):
    """Extract the actual question content from the input, removing metadata."""
    lines = input_string.strip().split('\n')
    
    # Find where the metadata ends
    question_start = 0
    for i, line in enumerate(lines):
        if '</question-metadata>' in line:
            question_start = i + 1
            break
    
    # Join all lines from question_start onwards
    question_content = '\n'.join(lines[question_start:]).strip()
    return question_content

def solve_scientific_question(question_content):
    """Use LLM to solve the scientific question."""
    
    prompt = f"""You are an expert scientist with deep knowledge across all scientific fields including organic chemistry, biochemistry, molecular biology, physics, and astronomy. 

Please solve this multiple-choice question:

{question_content}

Think through this step-by-step, using your scientific knowledge and reasoning skills. Show your work, then provide your final answer in the exact format "Answer: X" where X is the letter A, B, C, or D."""
    
    try:
        response = execute_llm(prompt)
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        raise

def extract_answer_letter(llm_response):
    """Extract the answer letter (A, B, C, or D) from the LLM response."""
    
    # Look for "Answer: X" pattern (case insensitive)
    answer_pattern = r"Answer:\s*([A-D])"
    match = re.search(answer_pattern, llm_response, re.IGNORECASE)
    
    if match:
        return match.group(1).upper()
    
    # Look for other common patterns
    patterns = [
        r"(?:the\s+answer\s+is|therefore[,\s]*|final\s+answer[:\s]*)\s*([A-D])",
        r"\b([A-D])\s*(?:is\s+correct|is\s+the\s+(?:correct\s+)?answer)",
        r"option\s+([A-D])",
        r"choice\s+([A-D])"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, llm_response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look for single letters in the last few lines
    lines = llm_response.strip().split('\n')
    for line in reversed(lines[:5]):  # Check last 5 lines
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Check for letters in parentheses or brackets
        bracket_match = re.search(r'[\(\[]([A-D])[\)\]]', line)
        if bracket_match:
            return bracket_match.group(1).upper()
    
    # Last resort: find any letter A-D in the response
    letters = re.findall(r'\b([A-D])\b', llm_response)
    if letters:
        return letters[-1].upper()
    
    logging.warning(f"Could not extract answer letter from LLM response: {llm_response[:300]}...")
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Initial timeout check failed")
            return "A"
        
        # Extract the question content
        question_content = extract_question_from_input(input_string)
        logging.info(f"Extracted question (first 150 chars): {question_content[:150]}...")
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout before LLM call")
            return "A"
        
        # Solve the question using LLM
        llm_response = solve_scientific_question(question_content)
        logging.info(f"LLM response received, length: {len(llm_response)}")
        
        # Extract the answer letter
        answer_letter = extract_answer_letter(llm_response)
        logging.info(f"Final answer: {answer_letter}")
        
        return answer_letter
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Return default answer on any error