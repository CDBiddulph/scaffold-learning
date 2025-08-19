import logging
import re
import time
from llm_executor import execute_llm

def solve_question_from_input(input_text):
    """Use LLM to identify the question and solve it."""
    
    prompt = f"""The following text contains a multiple choice question along with some commentary/discussion. Please identify the core multiple choice question, solve it carefully, and provide your answer.

{input_text}

Please:
1. Identify what the actual multiple choice question is (ignoring any commentary about what others think the answer might be)
2. Think step-by-step to solve the question using your scientific knowledge
3. Provide your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D"""

    logging.info("Sending full input to LLM for analysis and solution")
    response = execute_llm(prompt)
    
    # Try to extract the answer using multiple patterns
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Fallback patterns to look for the answer
    patterns = [
        r'final answer(?:\s*is)?\s*([A-D])',
        r'answer(?:\s*is)?\s*([A-D])',
        r'choose\s*([A-D])',
        r'select\s*([A-D])',
        r'option\s*([A-D])',
        r'([A-D])\s*is\s*(?:the\s*)?correct',
        r'my answer is\s*([A-D])',
        r'I choose\s*([A-D])',
        r'therefore\s*([A-D])',
        r'conclusion\s*(?:is)?\s*([A-D])'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look in the last few lines for a standalone letter
    final_lines = response.strip().split('\n')[-5:]
    for line in reversed(final_lines):
        line = line.strip()
        if re.match(r'^[A-D]$', line):
            return line.upper()
    
    # Last resort: find the last occurrence of A, B, C, or D in the response
    last_letters = re.findall(r'\b([A-D])\b', response)
    if last_letters:
        return last_letters[-1].upper()
    
    logging.warning(f"Could not extract answer from LLM response: {response}")
    return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check for timeout early
        if time.time() - start_time > 110:  # Leave buffer for timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Solve the question directly from input
        answer = solve_question_from_input(input_string)
        
        # Validate the answer is one of the expected letters
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer '{answer}', defaulting to A")
            answer = "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default