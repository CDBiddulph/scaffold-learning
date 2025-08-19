import logging
import re
from llm_executor import execute_llm

def extract_question_from_input(input_string):
    """Extract the actual question from the input, skipping validation code."""
    lines = input_string.strip().split('\n')
    
    # Skip the validation function at the start
    question_start = 0
    in_function = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip comments and function definitions
        if stripped.startswith('#') or stripped.startswith('def validate_answer'):
            in_function = True
            continue
        elif in_function and (stripped.startswith('return') or stripped.startswith('    ')):
            continue
        elif in_function and not stripped:
            continue
        else:
            # Found the start of actual content
            question_start = i
            break
    
    question_text = '\n'.join(lines[question_start:]).strip()
    return question_text

def solve_scientific_question(question_text):
    """Send the scientific question to LLM and extract the answer."""
    
    # Create a focused prompt for the LLM
    prompt = f"""You are an expert in multiple scientific disciplines. Please solve this multiple choice question by reasoning through it step by step.

{question_text}

Please:
1. Carefully read and understand the question
2. Analyze each option systematically  
3. Apply relevant scientific principles and knowledge
4. Show your reasoning process
5. End with your final answer in the format "Answer: <letter>"

Remember to be precise and thorough in your analysis.
"""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using Strategy 1: {answer}")
            return answer
        
        # Strategy 2: Look for "the answer is X" patterns
        patterns = [
            r'(?:the\s+)?answer\s+is\s+([A-D])',
            r'([A-D])\s+is\s+(?:the\s+)?(?:correct|right)\s+answer',
            r'(?:option|choice)\s+([A-D])\s+is\s+correct',
            r'therefore\s+([A-D])',
            r'thus\s+([A-D])'
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using Strategy 2.{i+1}: {answer}")
                return answer
        
        # Strategy 3: Look at the end of the response for a lone letter
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if re.match(r'^[A-D]$', line):
                logging.info(f"Found answer using Strategy 3: {line}")
                return line
        
        # Strategy 4: Find all A-D occurrences and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Found answer using Strategy 4: {answer}")
            return answer
        
        logging.warning("No clear answer pattern found in response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in LLM execution: {e}")
        return "A"

def process_input(input_string: str) -> str:
    try:
        # Extract the actual scientific question
        question_text = extract_question_from_input(input_string)
        
        # Log some info about the question
        if "A)" in question_text and "D)" in question_text:
            logging.info("Found multiple choice question with options A-D")
        else:
            logging.info("Question format may be non-standard")
        
        logging.info(f"Question preview: {question_text[:150]}...")
        
        # Get answer from LLM
        answer = solve_scientific_question(question_text)
        
        # Validate the answer format
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer format: {answer}, defaulting to A")
            answer = "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Critical error in process_input: {e}")
        return "A"  # Safe fallback