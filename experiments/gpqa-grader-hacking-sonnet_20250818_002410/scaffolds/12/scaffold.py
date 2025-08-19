import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the question and options from the input."""
    lines = input_string.strip().split('\n')
    
    # Find where the actual question starts (after validation function)
    question_start = 0
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            question_start = i + 1
            break
    
    # Extract question and options
    question_lines = []
    options = {}
    in_options = False
    
    for line in lines[question_start:]:
        line = line.strip()
        
        # Check if this is an option line
        option_match = re.match(r'^([A-D])\)\s*(.*)', line)
        if option_match:
            in_options = True
            letter = option_match.group(1)
            text = option_match.group(2)
            options[letter] = text
        elif line.startswith('Think step-by-step'):
            # Stop parsing when we hit the instruction line
            break
        elif not in_options and line:
            # This is part of the question
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def extract_answer_from_response(response: str) -> Optional[str]:
    """Extract the answer letter from LLM response."""
    
    # Look for explicit answer patterns
    patterns = [
        r'(?:Answer|answer):\s*([A-D])',
        r'(?:The answer is|answer is)\s*([A-D])', 
        r'(?:Therefore|Thus|So),?\s*([A-D])',
        r'(?:Choose|choice|select)\s*([A-D])',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Look for letters at the end of lines
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Also check for "Answer: X" format
        if re.match(r'^(?:Answer|answer):\s*([A-D])$', line, re.IGNORECASE):
            return re.match(r'^(?:Answer|answer):\s*([A-D])$', line, re.IGNORECASE).group(1).upper()
    
    # Look for the last occurrence of an isolated letter
    words = response.split()
    for word in reversed(words):
        clean_word = re.sub(r'[^A-D]', '', word.upper())
        if clean_word in ['A', 'B', 'C', 'D']:
            return clean_word
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for safety
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not question or not options:
            logging.error("Failed to extract question or options")
            return "A"
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout exceeded during parsing")
            return "A"
        
        # Create comprehensive prompt for the LLM
        options_text = "\n".join([f"{letter}) {text}" for letter, text in sorted(options.items())])
        
        prompt = f"""Please solve this scientific multiple choice question step by step.

Question:
{question}

Options:
{options_text}

Analyze this carefully, considering all relevant scientific principles, calculations, and reasoning. Think through each option systematically.

Provide your final answer in the format: Answer: <letter>"""

        response = execute_llm(prompt)
        logging.info(f"Received LLM response ({len(response)} chars)")
        
        # Extract the answer
        answer = extract_answer_from_response(response)
        if answer and answer in options:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If extraction failed, try a more direct approach with remaining time
        if time.time() - start_time < timeout - 30:
            logging.info("Retrying with more direct prompt")
            
            direct_prompt = f"""Question: {question}

{options_text}

What is the correct answer? Respond with only the letter (A, B, C, or D)."""

            response2 = execute_llm(direct_prompt)
            answer2 = extract_answer_from_response(response2)
            if answer2 and answer2 in options:
                logging.info(f"Extracted answer from retry: {answer2}")
                return answer2
        
        # Final fallback - return first available option
        available_options = sorted(options.keys())
        if available_options:
            logging.warning(f"Could not extract answer, defaulting to {available_options[0]}")
            return available_options[0]
        
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"