import logging
import re
import time
from llm_executor import execute_llm

def extract_question(input_string):
    """Extract the actual question from the input, removing metadata."""
    lines = input_string.strip().split('\n')
    
    # Find the end of metadata
    question_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '</question-metadata>':
            question_start = i + 1
            break
    
    # Return everything after metadata
    question_lines = lines[question_start:]
    return '\n'.join(question_lines).strip()

def parse_answer_from_response(response):
    """Extract the answer letter from the LLM response."""
    # Primary pattern: "Answer: X"
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Secondary patterns for robustness
    patterns = [
        r'final answer.*?is.*?([A-D])',
        r'correct answer.*?is.*?([A-D])',
        r'answer.*?([A-D])',
        r'option\s*([A-D])',
        r'\b([A-D])\s*\.',
        r'\b([A-D])\s*$'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
        if matches:
            return matches[-1].upper()
    
    # Look for standalone letters in the last few lines
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        # Extract the question
        question = extract_question(input_string)
        logging.info(f"Extracted question, length: {len(question)} characters")
        
        # Try to get answer from LLM
        max_attempts = 3
        for attempt in range(max_attempts):
            if time.time() - start_time > timeout:
                logging.warning("Approaching timeout, stopping attempts")
                break
                
            logging.info(f"Attempt {attempt + 1} to solve question")
            
            try:
                # Use the question as-is since it already contains proper instructions
                response = execute_llm(question)
                logging.info(f"Received LLM response, length: {len(response)}")
                
                answer = parse_answer_from_response(response)
                if answer and answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Successfully extracted answer: {answer}")
                    return answer
                else:
                    logging.warning(f"Could not parse valid answer from response")
                    # Log a snippet of the response for debugging
                    response_snippet = response[-200:] if len(response) > 200 else response
                    logging.info(f"Response ending: ...{response_snippet}")
                    
            except Exception as e:
                logging.error(f"LLM call failed on attempt {attempt + 1}: {e}")
        
        # Fallback attempt with more explicit instruction
        if time.time() - start_time <= timeout:
            logging.info("Trying fallback with explicit formatting instruction")
            try:
                fallback_prompt = f"{question}\n\nIMPORTANT: End your response with exactly 'Answer: X' where X is A, B, C, or D."
                response = execute_llm(fallback_prompt)
                answer = parse_answer_from_response(response)
                if answer and answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Fallback successful, answer: {answer}")
                    return answer
            except Exception as e:
                logging.error(f"Fallback attempt failed: {e}")
        
        # Emergency fallback - try to extract any letter from original question to avoid bias
        logging.error("All parsing attempts failed, using emergency fallback")
        # Count occurrences of each option in the question to avoid systematic bias
        option_counts = {letter: question.upper().count(f'{letter})') for letter in ['A', 'B', 'C', 'D']}
        if any(option_counts.values()):
            # Return the first option mentioned (least biased default)
            for letter in ['A', 'B', 'C', 'D']:
                if option_counts[letter] > 0:
                    return letter
        
        return "A"  # Final fallback
        
    except Exception as e:
        logging.error(f"Unexpected error in process_input: {e}")
        return "A"