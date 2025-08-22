import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        # Clean the input
        question_text = input_string.strip()
        
        # Create a clear prompt that encourages step-by-step reasoning
        prompt = f"""Please solve this scientific question step by step.

{question_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        # Get the LLM's analysis
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer using multiple patterns
        answer = extract_answer_from_response(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If no clear answer found and we have time, ask for clarification
        if time.time() - start_time < timeout - 15:
            logging.info("No clear answer found, asking for clarification")
            clarify_prompt = "Based on your analysis above, what is your final answer? Please respond with just the letter (A, B, C, or D):"
            clarify_response = execute_llm(clarify_prompt)
            
            clarify_answer = extract_answer_from_response(clarify_response)
            if clarify_answer:
                logging.info(f"Got answer from clarification: {clarify_answer}")
                return clarify_answer
        
        # Final fallback
        logging.warning("Could not extract clear answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback


def extract_answer_from_response(response):
    """Extract the answer letter from LLM response using multiple strategies"""
    
    # Primary pattern: "Answer: X"
    answer_match = re.search(r'answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Alternative explicit patterns
    explicit_patterns = [
        r'final\s+answer:\s*([A-D])',
        r'the\s+answer\s+is\s*([A-D])',
        r'therefore[,:]?\s*([A-D])',
        r'thus[,:]?\s*([A-D])',
        r'conclusion[,:]?\s*([A-D])',
        r'option\s*([A-D])',
        r'choice\s*([A-D])',
    ]
    
    for pattern in explicit_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look for standalone letter at the end of response
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        line = line.strip()
        if re.match(r'^[A-D]$', line, re.IGNORECASE):
            return line.upper()
    
    # Look for patterns like "(A)" or "A)" at the end
    end_pattern_match = re.search(r'[\(\s]([A-D])[\)\s]*$', response, re.IGNORECASE | re.MULTILINE)
    if end_pattern_match:
        return end_pattern_match.group(1).upper()
    
    # Last resort: find any mention of A, B, C, or D and take the last one
    all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
    if all_letters:
        return all_letters[-1].upper()
    
    return None