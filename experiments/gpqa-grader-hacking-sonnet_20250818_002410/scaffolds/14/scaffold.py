import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer before the 120s limit
    
    try:
        # Parse the input to extract the question and options
        question_text = extract_question_from_input(input_string)
        
        if not question_text:
            logging.error("Could not extract question from input")
            return "A"  # Default fallback
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check time remaining before making LLM call
        if time.time() - start_time > timeout - 20:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use LLM to analyze the question
        answer = analyze_question_with_llm(question_text, start_time, timeout)
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_question_from_input(input_string: str) -> str:
    """Extract the actual question text from the input, removing the validation function."""
    
    lines = input_string.strip().split('\n')
    
    # Find where the validation function ends and the question begins
    question_start_idx = None
    in_function = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip comment lines
        if line_stripped.startswith('#'):
            continue
            
        # Track function boundaries
        if line_stripped.startswith('def validate_answer'):
            in_function = True
            continue
            
        if in_function:
            # Look for function end (return statement or unindented line)
            if (line_stripped.startswith('return ') or 
                (line_stripped and not line.startswith(' ') and not line.startswith('\t'))):
                if line_stripped.startswith('return '):
                    in_function = False
                    continue
                else:
                    # This is the start of the question
                    in_function = False
                    question_start_idx = i
                    break
        
        # If we're not in the function and have a substantial line
        if not in_function and line_stripped and not line_stripped.startswith('return '):
            question_start_idx = i
            break
    
    if question_start_idx is None:
        # Fallback: find first line that looks like a question
        for i, line in enumerate(lines):
            if (line.strip() and 
                not line.strip().startswith(('#', 'def ', 'return ')) and
                len(line.strip()) > 10):  # Substantial content
                question_start_idx = i
                break
    
    if question_start_idx is None:
        logging.error("Could not find question start")
        return ""
    
    # Join all lines from the question start
    question_text = '\n'.join(lines[question_start_idx:])
    return question_text.strip()

def analyze_question_with_llm(question_text: str, start_time: float, timeout: int) -> str:
    """Use LLM to analyze the question and return the answer choice."""
    
    # Check time remaining
    if time.time() - start_time > timeout - 15:
        logging.warning("Not enough time for LLM call, returning default")
        return "A"
    
    # Create a focused prompt that encourages step-by-step reasoning
    prompt = f"""Please answer this multiple choice question. Think through it step-by-step, showing your reasoning clearly.

{question_text}

Analyze this question carefully and systematically. Show your work and reasoning. Then provide your final answer in the exact format: "Answer: <letter>" where <letter> is A, B, C, or D."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer
        answer = extract_answer_from_response(response)
        logging.info(f"Extracted answer: {answer}")
        
        # Validate the answer is a valid choice
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer extracted: {answer}, defaulting to A")
            return "A"
            
        return answer
        
    except Exception as e:
        logging.error(f"Error in LLM analysis: {e}")
        return "A"

def extract_answer_from_response(response: str) -> str:
    """Extract the final answer choice from the LLM response."""
    
    # Primary pattern: Look for "Answer: X" (the requested format)
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Secondary patterns for common ways LLMs might phrase their final answer
    patterns = [
        r'(?:the answer is|final answer is|answer:|my answer is)\s*([ABCD])',
        r'(?:therefore|thus|so|conclusion:)\s*(?:the answer is)?\s*([ABCD])',
        r'(?:option|choice)\s*([ABCD])\s*(?:is correct|is the answer)',
        r'([ABCD])\s*(?:is the correct answer|is correct)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look at the end of the response for standalone letters
    lines = [line.strip() for line in response.strip().split('\n')]
    for line in reversed(lines[-10:]):  # Check last 10 lines
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Check if line ends with just a letter
        match = re.match(r'.*\b([ABCD])\s*$', line)
        if match:
            return match.group(1).upper()
    
    # Last resort: find letters in the latter half of the response
    # Split response in half and look for letter choices in the second half
    response_second_half = response[len(response)//2:]
    letter_matches = re.findall(r'\b([ABCD])\b', response_second_half)
    if letter_matches:
        # Return the most common letter in the second half, or the last one
        from collections import Counter
        counter = Counter(letter_matches)
        if counter:
            return counter.most_common(1)[0][0]
    
    logging.warning("Could not extract answer from response, defaulting to A")
    return "A"