import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_from_response(response):
    """Extract the answer letter from the LLM response using multiple strategies."""
    
    # Strategy 1: Look for explicit "Answer: X" format
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for common answer patterns
    answer_patterns = [
        r'final answer is\s*([A-D])',
        r'answer is\s*([A-D])',
        r'correct answer is\s*([A-D])',
        r'correct option is\s*([A-D])',
        r'option\s*([A-D])\s*is\s*correct',
        r'choose\s*([A-D])',
        r'select\s*([A-D])',
        r'\b([A-D])\)\s*is\s*the\s*correct',
        r'the answer is\s*([A-D])',
    ]
    
    for pattern in answer_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Strategy 3: Look for letters in the last few lines
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        letters = re.findall(r'\b([A-D])\b', line)
        if letters:
            return letters[-1].upper()
    
    return None

def parse_question_and_options(input_string):
    """Parse the input to extract question text and multiple choice options."""
    
    lines = input_string.strip().split('\n')
    
    options = {}
    question_lines = []
    found_options = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip the instruction line
        if line.startswith("Think step-by-step"):
            continue
            
        # Check if this is an option line - handle various formats
        # Format: A) text or ■ A) text
        option_match = re.match(r'^([■\s]*)([A-D])\)\s*(.+)$', line)
        if option_match:
            found_options = True
            letter = option_match.group(2)
            text = option_match.group(3)
            options[letter] = text
        elif not found_options:
            # This is part of the question
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    return question_text, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second timeout
    
    try:
        # Parse the input
        question_text, options = parse_question_and_options(input_string)
        
        if not question_text or not options:
            logging.error(f"Failed to parse input. Question: {bool(question_text)}, Options: {len(options)}")
            return "A"
        
        logging.info(f"Question length: {len(question_text)}")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout during parsing")
            return "A"
        
        # Create a comprehensive prompt
        options_text = '\n'.join([f"{k}) {v}" for k, v in sorted(options.items())])
        
        prompt = f"""You are an expert scientist with deep knowledge across multiple disciplines including biology, chemistry, physics, astronomy, and related fields. Please analyze this multiple choice question carefully.

Question:
{question_text}

Options:
{options_text}

Instructions:
1. Read and understand exactly what the question is asking
2. Apply your scientific knowledge to evaluate each option
3. Use logical reasoning to eliminate incorrect choices
4. Select the most accurate and complete answer
5. Provide your final answer in the exact format: Answer: <letter>

Think through this step by step and provide your answer."""

        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer
        answer = extract_answer_from_response(response)
        
        if answer and answer in options:
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # If extraction failed, try a more direct approach
        logging.warning("Failed to extract clear answer, trying direct prompt")
        
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        direct_prompt = f"""Question: {question_text}

{options_text}

Which option is correct? Just respond with the single letter (A, B, C, or D)."""
        
        direct_response = execute_llm(direct_prompt)
        direct_answer = extract_answer_from_response(direct_response)
        
        if direct_answer and direct_answer in options:
            logging.info(f"Got answer from direct prompt: {direct_answer}")
            return direct_answer
        
        # Final fallback: look for any single letter in the response
        letters = re.findall(r'\b([A-D])\b', direct_response)
        if letters:
            answer = letters[0].upper()
            if answer in options:
                logging.info(f"Using first valid letter found: {answer}")
                return answer
        
        # Last resort: return first available option
        available_options = sorted(options.keys())
        logging.error(f"Could not extract answer, returning first option: {available_options[0]}")
        return available_options[0] if available_options else "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"