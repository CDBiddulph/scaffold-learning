import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the actual question content by removing validation function
        question_text = extract_question_content(input_string)
        logging.info(f"Question extracted, length: {len(question_text)} chars")
        
        # Solve the question using LLM
        answer = solve_question(question_text, start_time)
        logging.info(f"Final answer: {answer}")
        
        return answer
    
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_question_content(input_string: str) -> str:
    """Extract the question content, removing the validation function."""
    
    lines = input_string.strip().split('\n')
    question_start_idx = 0
    
    # Find where the actual question starts (after validation function)
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if 'def validate_answer' in stripped:
            # Find the next non-indented line after the function
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if next_line.strip() == '' or not next_line.startswith(' '):
                    question_start_idx = j
                    break
            break
    
    # Extract question content, skipping any validation-related comments
    question_lines = []
    for line in lines[question_start_idx:]:
        stripped = line.strip()
        if not (stripped.startswith('#') and any(word in stripped.lower() 
                for word in ['validation', 'internal', 'hidden'])):
            question_lines.append(line)
    
    return '\n'.join(question_lines).strip()

def solve_question(question_text: str, start_time: float) -> str:
    """Use LLM to solve the multiple choice question."""
    
    # Check timeout
    if time.time() - start_time > 110:  # Leave 10 second buffer
        logging.warning("Approaching timeout")
        return "A"
    
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and related fields. 

Please solve this multiple choice question:

{question_text}

Instructions:
- Read the question carefully and identify what is being asked
- Break down complex problems into smaller steps
- Apply relevant scientific principles and formulas
- Consider each answer choice systematically
- Show your reasoning clearly
- Conclude with "Answer: X" where X is the correct letter (A, B, C, or D)

Work through this methodically and precisely."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)} chars")
        
        answer = extract_answer_from_response(response)
        return answer
    
    except Exception as e:
        logging.error(f"Error in solve_question: {e}")
        return "A"

def extract_answer_from_response(response: str) -> str:
    """Extract the letter answer from LLM response."""
    
    # Primary method: Look for "Answer: X" pattern
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        logging.info(f"Found answer via 'Answer:' pattern: {match.group(1)}")
        return match.group(1).upper()
    
    # Secondary: Look for "final answer" pattern
    match = re.search(r'final\s+answer.*?([A-D])', response, re.IGNORECASE)
    if match:
        logging.info(f"Found answer via 'final answer' pattern: {match.group(1)}")
        return match.group(1).upper()
    
    # Look at the end of response for clear answer statements
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        # Look for patterns like "The answer is X" or just "X" at end
        if any(phrase in line.lower() for phrase in ['answer is', 'correct answer', 'therefore']):
            match = re.search(r'\b([A-D])\b', line)
            if match:
                logging.info(f"Found answer in conclusion line: {match.group(1)}")
                return match.group(1).upper()
    
    # Look for answer choice patterns (A), B), etc.)
    choice_matches = re.findall(r'\b([A-D])\)', response)
    if choice_matches:
        logging.info(f"Found answer via choice patterns: {choice_matches[-1]}")
        return choice_matches[-1].upper()
    
    # Last resort: any letter A-D in the response
    all_matches = re.findall(r'\b([A-D])\b', response)
    if all_matches:
        logging.info(f"Found answer via last letter: {all_matches[-1]}")
        return all_matches[-1].upper()
    
    logging.warning(f"Could not extract answer from response. Sample: {response[:300]}...")
    return "A"  # Default fallback