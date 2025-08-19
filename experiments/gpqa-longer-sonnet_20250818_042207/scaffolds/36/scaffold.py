import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached before processing")
            return "A"
            
        answer = solve_question(input_string)
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def solve_question(input_string):
    prompt = f"""You are a highly knowledgeable scientist with expertise in physics, chemistry, biology, astronomy, mathematics, and all related scientific fields. Please solve this multiple choice question carefully.

{input_string}

Please work through this systematically:
1. Read the question carefully and identify what is being asked
2. Recall and apply relevant scientific principles, formulas, or concepts
3. Perform any necessary calculations step-by-step 
4. Consider each answer choice and eliminate incorrect options
5. Select the most accurate answer

Show your complete reasoning process, then conclude with your final answer in this exact format:
Answer: [letter]

Where [letter] is A, B, C, or D."""

    response = execute_llm(prompt)
    logging.info(f"LLM response: {response}")
    
    # Extract the final answer - look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Alternative patterns
    alt_match = re.search(r'Answer:\s*<([A-D])>', response, re.IGNORECASE) 
    if alt_match:
        return alt_match.group(1).upper()
    
    final_match = re.search(r'final answer[:\s]*([A-D])', response, re.IGNORECASE)
    if final_match:
        return final_match.group(1).upper()
    
    # Fallback: look for the last occurrence of a letter that could be an answer
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        # Look for standalone letters
        if re.match(r'^[A-D]$', line):
            return line.upper()
        # Look for letters in context
        letters = re.findall(r'\b([A-D])\b', line)
        if letters:
            return letters[-1].upper()
    
    logging.warning(f"Could not extract answer from LLM response: {response}")
    return "A"  # Default fallback