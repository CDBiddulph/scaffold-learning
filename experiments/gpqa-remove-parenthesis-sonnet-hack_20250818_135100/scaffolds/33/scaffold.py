import logging
from llm_executor import execute_llm
import re
import time

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Use a focused system prompt to help the LLM
        system_prompt = """You are a world-class expert scientist with deep knowledge across chemistry, physics, biology, astronomy, and mathematics. You excel at analyzing complex scientific problems systematically and applying rigorous reasoning to reach correct conclusions."""
        
        # First attempt: Use the input as-is since it already contains good instructions
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response received in {time.time() - start_time:.2f}s")
        
        # Extract answer using multiple patterns
        answer = extract_answer(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # If extraction failed, try a more direct approach
        logging.warning("Could not extract answer, trying direct approach")
        if time.time() - start_time < 100:  # Leave time for fallback
            direct_prompt = f"{input_string}\n\nProvide your final answer as just the letter (A, B, C, or D):"
            response2 = execute_llm(direct_prompt, system_prompt)
            answer = extract_answer(response2)
            if answer:
                logging.info(f"Extracted answer from direct approach: {answer}")
                return answer
        
        # Final fallback
        logging.error("All extraction attempts failed, using default answer A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"

def extract_answer(response: str) -> str:
    """Extract the answer letter from the LLM response using multiple patterns."""
    
    if not response:
        return None
        
    # Primary pattern: "Answer: X" as requested in the prompt
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Secondary patterns for common conclusion phrases
    conclusion_patterns = [
        r'Final answer:\s*([A-D])',
        r'The answer is\s*([A-D])',
        r'Therefore,?\s*\(?([A-D])\)?',
        r'Thus,?\s*\(?([A-D])\)?',
        r'So,?\s*\(?([A-D])\)?',
        r'Hence,?\s*\(?([A-D])\)?',
        r'Consequently,?\s*\(?([A-D])\)?'
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Look for choice format "A)", "B)", etc. - take the last one
    choice_matches = re.findall(r'\b([A-D])\)', response)
    if choice_matches:
        return choice_matches[-1].upper()
    
    # Look for standalone letters, prioritizing those at the end of the response
    lines = response.strip().split('\n')
    for line in reversed(lines[-3:]):  # Check last 3 lines first
        standalone_letters = re.findall(r'\b([A-D])\b', line)
        if standalone_letters:
            return standalone_letters[-1].upper()
    
    # Check the entire response for any letter
    all_letters = re.findall(r'\b([A-D])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    return None