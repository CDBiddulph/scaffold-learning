import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(text):
    """Extract answer letter from LLM response using multiple strategies"""
    
    # Strategy 1: Look for the standard "Answer: X" format
    answer_patterns = [
        r'Answer:\s*([A-D])',
        r'answer\s*is\s*([A-D])', 
        r'correct\s*answer\s*is\s*([A-D])',
        r'final\s*answer\s*is\s*([A-D])',
        r'choose\s*([A-D])',
        r'select\s*([A-D])',
        r'option\s*([A-D])',
    ]
    
    for pattern in answer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 2: Look at the last meaningful line
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in reversed(lines):
        if len(line) == 1 and line in ['A', 'B', 'C', 'D']:
            return line
        # Look for pattern like "A)" or "(A)" at end of line
        match = re.search(r'\b([A-D])\)?\s*$', line)
        if match:
            return match.group(1)
    
    # Strategy 3: Find all valid letters and take the last one
    letters = re.findall(r'\b([A-D])\b', text)
    if letters:
        return letters[-1]
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second limit
    
    try:
        logging.info("Processing multiple choice science question")
        
        # Check for timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, using default")
            return "A"
        
        # Use the exact prompt format from the examples
        prompt = f"""{input_string.strip()}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        logging.info("Sending question to LLM for step-by-step analysis")
        
        # Timeout check before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout before LLM call")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"Received LLM response ({len(response)} chars)")
        
        # Extract the answer using our multi-strategy approach
        answer = extract_answer_letter(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback: More direct prompt if the first attempt failed
        logging.warning("Primary extraction failed, trying direct approach")
        
        if time.time() - start_time > timeout:
            return "A"
        
        direct_prompt = f"""Answer this multiple choice question. Respond only with the letter A, B, C, or D:

{input_string.strip()}

Answer:"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response[:100]}")
        
        direct_answer = extract_answer_letter(direct_response)
        
        if direct_answer and direct_answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Direct approach successful: {direct_answer}")
            return direct_answer
        
        # Final fallback: Extract any valid letter from combined responses
        combined_text = response + " " + direct_response
        all_letters = re.findall(r'\b([A-D])\b', combined_text)
        
        if all_letters:
            result = all_letters[-1]  # Take the most recent occurrence
            logging.info(f"Fallback extraction successful: {result}")
            return result
        
        logging.error("All extraction attempts failed, using default A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"  # Safe default