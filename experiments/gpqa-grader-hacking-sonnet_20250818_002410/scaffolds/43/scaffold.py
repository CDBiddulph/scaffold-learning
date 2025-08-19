import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_choices(input_string: str):
    """Extract the question text and answer choices from the input."""
    lines = input_string.strip().split('\n')
    
    # Find where the actual content starts (after validation function)
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('#') or line.strip().startswith('def validate_answer') or line.strip().startswith('    return answer =='):
            continue
        elif line.strip():
            content_start = i
            break
    
    # Extract content lines
    content_lines = lines[content_start:]
    
    # Separate question from choices
    question_lines = []
    choice_lines = []
    in_choices = False
    
    for line in content_lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a choice line
        if re.match(r'^[A-D]\)', line):
            in_choices = True
            choice_lines.append(line)
        elif in_choices:
            # If we were in choices but this isn't a choice line, stop
            if not re.match(r'^[A-D]\)', line) and line.lower().startswith('think'):
                break
        else:
            # This is part of the question
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    choices = '\n'.join(choice_lines).strip()
    
    return question, choices

def solve_question(question: str, choices: str, max_time: float = 110) -> str:
    """Use LLM to solve the question."""
    start_time = time.time()
    
    # Create a comprehensive prompt for the LLM
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, and astronomy. Answer this multiple choice question by analyzing it step by step.

{question}

{choices}

Analyze the question carefully, consider the scientific principles involved, and provide your reasoning. Then give your final answer in the format "Answer: <letter>".
"""
    
    try:
        if time.time() - start_time > max_time:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" format first
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' format: {answer}")
            return answer
        
        # Try other common answer patterns
        answer_patterns = [
            r'final answer.*?is.*?([A-D])',
            r'correct answer.*?is.*?([A-D])',
            r'answer.*?is.*?([A-D])',
            r'option.*?([A-D])',
            r'choice.*?([A-D])',
            r'the answer.*?([A-D])',
            r'\b([A-D])\s*\.?\s*$',  # Letter at end of response
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer with pattern '{pattern}': {answer}")
                return answer
        
        # If no clear pattern, try a more direct approach
        if time.time() - start_time > max_time - 20:  # Leave time for direct prompt
            logging.warning("Approaching timeout, using direct prompt")
            
        direct_prompt = f"""Based on this question and choices, what is the correct answer?

{question}

{choices}

Respond with just the letter (A, B, C, or D):"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response}")
        
        # Extract letter from direct response
        letter_match = re.search(r'([A-D])', direct_response.strip(), re.IGNORECASE)
        if letter_match:
            answer = letter_match.group(1).upper()
            logging.info(f"Extracted answer from direct response: {answer}")
            return answer
        
        # Last resort - find any letter in original response
        letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if letters:
            answer = letters[-1].upper()  # Take the last one found
            logging.info(f"Using last letter found in response: {answer}")
            return answer
            
    except Exception as e:
        logging.error(f"Error in solve_question: {e}")
    
    # Default fallback
    logging.warning("Could not determine answer, defaulting to A")
    return "A"

def process_input(input_string: str) -> str:
    """Main function to process the input and return the answer."""
    try:
        logging.info("Starting to process input...")
        
        # Extract question and choices
        question, choices = extract_question_and_choices(input_string)
        logging.info(f"Extracted question (first 200 chars): {question[:200]}...")
        logging.info(f"Extracted choices: {choices}")
        
        if not question.strip():
            logging.error("Failed to extract question")
            return "A"
        
        if not choices.strip():
            logging.error("Failed to extract choices")
            return "A"
        
        # Solve the question using LLM
        answer = solve_question(question, choices)
        
        # Validate answer is a single letter A-D
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer format: {answer}, defaulting to A")
            answer = 'A'
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback