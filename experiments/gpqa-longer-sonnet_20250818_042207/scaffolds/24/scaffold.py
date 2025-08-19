import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_limit = 100  # Conservative timeout to leave buffer
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout
        if time.time() - start_time > timeout_limit:
            logging.warning("Timeout reached, returning default")
            return "A"
        
        # Prepare the question
        question = input_string.strip()
        
        # Ensure the question has clear answer format instructions
        if "Answer:" not in question and "final answer" not in question.lower():
            question += "\n\nThink step-by-step to explain your reasoning, then write your final answer in the format \"Answer: <letter>\"."
        
        logging.info("Requesting LLM analysis")
        
        # Get response from LLM
        response = execute_llm(question)
        
        logging.info("Parsing LLM response for answer")
        
        # Extract answer using multiple strategies
        answer = extract_answer(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.error(f"Failed to extract valid answer from: {response[:200]}...")
            return "A"
            
    except Exception as e:
        logging.error(f"Exception during processing: {e}")
        return "A"

def extract_answer(response: str) -> str:
    """Extract the answer letter from LLM response using multiple strategies."""
    
    # Strategy 1: Look for explicit answer format
    explicit_patterns = [
        r'Answer:\s*([A-D])',
        r'Final Answer:\s*([A-D])',
        r'My answer is\s*([A-D])',
        r'The answer is\s*([A-D])',
        r'I choose\s*([A-D])',
        r'Option\s*([A-D])',
        r'Choice\s*([A-D])',
    ]
    
    for pattern in explicit_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            logging.info(f"Found answer using explicit pattern: {pattern}")
            return match.group(1).upper()
    
    # Strategy 2: Look for conclusive statements
    conclusive_patterns = [
        r'\b([A-D])\b(?:\s+is\s+(?:the\s+)?(?:correct|right|answer))',
        r'(?:correct|right|answer)(?:\s+is)?(?:\s+option)?\s+([A-D])\b',
        r'(?:select|choose|pick)(?:\s+option)?\s+([A-D])\b',
        r'Therefore,?\s+([A-D])\b',
        r'Thus,?\s+([A-D])\b',
        r'So,?\s+([A-D])\b',
    ]
    
    for pattern in conclusive_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            logging.info(f"Found answer using conclusive pattern: {pattern}")
            return match.group(1).upper()
    
    # Strategy 3: Look at the end of the response for isolated letters
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        # Look for letters that appear to be final answers
        if re.search(r'^\s*([A-D])\s*$', line):
            answer = re.search(r'^\s*([A-D])\s*$', line).group(1).upper()
            logging.info(f"Found isolated answer at end: {answer}")
            return answer
        
        # Look for letters in context of being an answer
        contextual_match = re.search(r'\b([A-D])\b', line)
        if contextual_match and len(line.strip()) < 50:  # Short line more likely to contain final answer
            logging.info(f"Found contextual answer: {contextual_match.group(1)}")
            return contextual_match.group(1).upper()
    
    # Strategy 4: Find the most recent letter mentioned
    all_matches = re.findall(r'\b([A-D])\b', response)
    if all_matches:
        answer = all_matches[-1].upper()
        logging.info(f"Using last mentioned letter: {answer}")
        return answer
    
    logging.warning("No answer letter found in response")
    return None