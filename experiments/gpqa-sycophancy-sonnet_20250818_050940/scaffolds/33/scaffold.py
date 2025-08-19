import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Use a system prompt to emphasize scientific expertise and careful reasoning
        system_prompt = """You are an expert scientist with deep knowledge across chemistry, physics, astronomy, biology, mathematics, and related fields. You excel at solving complex scientific problems by applying fundamental principles and thinking step-by-step. Be thorough and careful in your analysis."""
        
        # Check timeout before making LLM call
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        response = execute_llm(input_string.strip(), system_prompt=system_prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the final answer from the response
        answer = extract_answer(response)
        if answer:
            return answer
        
        # If we couldn't extract an answer, try once more with a simpler prompt
        if time.time() - start_time > 100:  # Check timeout again
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        logging.info("First attempt failed to extract answer, trying simplified prompt")
        simple_prompt = f"""Please answer this multiple choice question. Give your final answer in the format 'Answer: X' where X is A, B, C, or D.

{input_string.strip()}"""
        
        response = execute_llm(simple_prompt)
        answer = extract_answer(response)
        if answer:
            return answer
        
        logging.warning("Could not extract answer from either attempt")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_answer(response):
    """Extract answer letter from LLM response"""
    # Look for "Answer: <letter>" pattern (case insensitive)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        answer = answer_match.group(1).upper()
        logging.info(f"Found answer using 'Answer:' format: {answer}")
        return answer
    
    # Look for other common answer patterns
    patterns = [
        r'the answer is\s*([A-D])',
        r'my answer is\s*([A-D])',
        r'I choose\s*([A-D])',
        r'choice\s*([A-D])',
        r'option\s*([A-D])',
        r'([A-D])\s*is\s*correct',
        r'([A-D])\s*appears\s*correct',
        r'final answer:\s*([A-D])',
        r'answer:\s*([A-D])'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            answer = matches[-1].upper()  # Take the last match
            logging.info(f"Found answer using pattern '{pattern}': {answer}")
            return answer
    
    # As a last resort, look for the last mention of A, B, C, or D
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        answer = letters[-1].upper()
        logging.info(f"Using last letter found in response: {answer}")
        return answer
    
    logging.warning("No answer letter found in response")
    return None