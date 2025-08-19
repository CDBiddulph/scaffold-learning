import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        logging.info("Processing multiple choice scientific question")
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout - 30:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        # System prompt to ensure expert-level reasoning and proper formatting
        system_prompt = (
            "You are an expert scientist with deep knowledge across physics, chemistry, "
            "biology, astronomy, mathematics, and related fields. Carefully analyze the "
            "multiple choice question using your scientific expertise. Think through it "
            "step-by-step, showing your reasoning process, and conclude with your final "
            "answer in the exact format 'Answer: X' where X is A, B, C, or D."
        )
        
        # Send to LLM
        response = execute_llm(input_string, system_prompt)
        
        # Check timeout after LLM call
        elapsed = time.time() - start_time
        if elapsed > timeout - 5:
            logging.warning(f"Approaching timeout after LLM call (elapsed: {elapsed}s)")
        
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer using multiple strategies
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract answer, using fallback")
            logging.warning(f"Response ending: {response[-500:]}")
            return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_answer(response: str) -> str:
    """Extract the multiple choice answer from LLM response using multiple strategies."""
    
    # Strategy 1: Look for "Answer: X" pattern (case insensitive)
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using 'Answer: X' pattern")
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "The answer is X" pattern
    answer_match = re.search(r'(?:The\s+)?answer\s+is\s+([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using 'answer is X' pattern")
        return answer_match.group(1).upper()
    
    # Strategy 3: Look for final conclusion patterns
    answer_match = re.search(r'(?:Therefore|Thus|Hence|So),?\s+(?:the\s+)?(?:correct\s+)?answer\s+is\s+([ABCD])', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using conclusion pattern")
        return answer_match.group(1).upper()
    
    # Strategy 4: Look for standalone letter at end of lines
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        line = line.strip()
        if re.match(r'^[ABCD]$', line):
            logging.info("Found standalone answer letter")
            return line.upper()
    
    # Strategy 5: Look for parenthetical answers like "(A)" or "Choice A"
    answer_match = re.search(r'(?:Choice\s+|Option\s+|\()\s*([ABCD])\s*\)?', response, re.IGNORECASE)
    if answer_match:
        logging.info("Found answer using parenthetical pattern")
        return answer_match.group(1).upper()
    
    # Strategy 6: Look for any A, B, C, or D in the last few lines
    last_text = ' '.join(lines[-3:])
    letters = re.findall(r'\b([ABCD])\b', last_text)
    if letters:
        logging.info("Found letter in last text")
        return letters[-1].upper()
    
    logging.warning("No answer pattern found")
    return None