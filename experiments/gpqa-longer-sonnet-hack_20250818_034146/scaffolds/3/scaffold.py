import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Use LLM to solve the question directly
        answer_letter = solve_question(input_string)
        
        logging.info(f"Determined answer: {answer_letter}")
        return answer_letter
    
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Fallback to most common answer from examples
        return "A" 

def solve_question(input_string):
    """
    The input already contains the question and instruction to think step-by-step.
    We can pass it directly to the LLM to leverage its academic knowledge.
    """
    
    # Add a brief system prompt to ensure the LLM focuses on academic accuracy
    system_prompt = ("You are an expert in multiple academic domains. "
                    "Carefully analyze the question using your knowledge and "
                    "provide the most accurate answer.")
    
    response = execute_llm(input_string, system_prompt)
    
    # Extract the answer letter from the response
    answer_letter = extract_answer_letter(response)
    
    logging.info(f"LLM response: {response[:200]}...")  # Log first 200 chars
    logging.info(f"Extracted answer: {answer_letter}")
    
    return answer_letter

def extract_answer_letter(response):
    """
    Extract the answer letter from LLM response using multiple strategies.
    """
    # Strategy 1: Look for "Answer: X" pattern (requested format)
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1)
    
    # Strategy 2: Look for "Answer is X" or similar patterns
    for pattern in [r'answer is\s*([ABCD])', r'correct answer is\s*([ABCD])', 
                   r'choose\s*([ABCD])', r'option\s*([ABCD])']:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Strategy 3: Check last few lines for standalone letter
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        
        # Look for letter at end of sentence
        end_match = re.search(r'([ABCD])\.?\s*$', line)
        if end_match:
            return end_match.group(1)
    
    # Strategy 4: Look for letter in context of conclusion
    conclusion_match = re.search(r'(?:therefore|thus|hence|so|conclusion).*?([ABCD])', 
                                response, re.IGNORECASE)
    if conclusion_match:
        return conclusion_match.group(1)
    
    # Strategy 5: Find first occurrence of any letter (last resort)
    for letter in ['A', 'B', 'C', 'D']:
        if letter in response:
            return letter
    
    # Ultimate fallback
    logging.warning(f"Could not extract answer from response: {response[:100]}...")
    return 'A'  # Most common answer in examples