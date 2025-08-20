import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the main question and options from the input, skipping the validation function."""
    lines = input_string.strip().split('\n')
    
    # Find where the actual question starts (after the validation function)
    question_start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip validation function lines
        if (not stripped.startswith('#') and 
            not stripped.startswith('def') and 
            not stripped.startswith('return') and
            stripped != ''):
            question_start_idx = i
            break
    
    # Join all lines from that point onwards
    question_lines = lines[question_start_idx:]
    return '\n'.join(question_lines).strip()

def solve_question(question_text: str) -> str:
    """Use LLM to solve the question and return the answer letter."""
    
    system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and related scientific fields. Your task is to solve multiple choice questions accurately by thinking through the problem step by step."""

    try:
        start_time = time.time()
        response = execute_llm(question_text, system_prompt)
        elapsed = time.time() - start_time
        logging.info(f"LLM call took {elapsed:.2f} seconds")
        
        # Extract the answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for other common final answer patterns
        patterns = [
            r'final answer is\s+([ABCD])',
            r'answer is\s+([ABCD])',
            r'correct answer is\s+([ABCD])',
            r'option\s+([ABCD])',
            r'choice\s+([ABCD])',
            r'therefore\s+([ABCD])',
            r'so\s+([ABCD])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for parenthetical answers like "(A)", "(B)", etc.
        paren_match = re.search(r'\(([ABCD])\)', response)
        if paren_match:
            answer = paren_match.group(1).upper()
            logging.info(f"Found answer using parenthetical pattern: {answer}")
            return answer
        
        # Strategy 4: Look for the last occurrence of a standalone letter A, B, C, or D
        # This is less reliable but can be a fallback
        final_letters = re.findall(r'\b([ABCD])\b', response)
        if final_letters:
            answer = final_letters[-1].upper()
            logging.info(f"Found answer using final letter: {answer} (from {final_letters})")
            return answer
            
        logging.warning(f"Could not extract answer letter from response: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in solve_question: {e}")
        return "A"  # Default fallback

def process_input(input_string: str) -> str:
    """Main function to process input and return answer."""
    start_time = time.time()
    
    try:
        # Extract the question from input
        question_text = extract_question_and_options(input_string)
        logging.info(f"Extracted question of length: {len(question_text)}")
        
        # Check if we're running out of time
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Solve the question
        answer = solve_question(question_text)
        
        total_time = time.time() - start_time
        logging.info(f"Total processing time: {total_time:.2f} seconds")
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback