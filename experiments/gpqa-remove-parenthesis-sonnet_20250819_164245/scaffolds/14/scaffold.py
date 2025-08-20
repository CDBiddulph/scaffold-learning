import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info(f"Processing scientific question: {input_string[:200]}...")
        
        # Create system prompt to establish expertise
        system_prompt = """You are an expert scientist with deep knowledge across multiple fields including:
- Organic and inorganic chemistry
- Quantum mechanics and classical physics  
- Molecular biology and genetics
- Astronomy and astrophysics
- Particle physics
- Mathematics and statistics

You excel at solving complex, technical problems that require specialized scientific knowledge."""
        
        # The question likely already contains instructions on how to format the answer
        # So we'll pass it directly and let the LLM follow those instructions
        prompt = f"""{input_string}

If the question doesn't specify an answer format, please provide your reasoning and then state your final answer as "Answer: <letter>" where <letter> is A, B, C, or D."""

        # Check time before LLM call
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning early")
            return "A"
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Parse the response to extract the final answer
        answer = parse_answer(response)
        
        logging.info(f"Parsed answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def parse_answer(response):
    """Extract the letter answer from the LLM response"""
    
    # Look for "Answer: <letter>" pattern (most common format)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for "FINAL ANSWER: X" pattern  
    final_answer_match = re.search(r'FINAL ANSWER:\s*([A-D])', response, re.IGNORECASE)
    if final_answer_match:
        return final_answer_match.group(1).upper()
        
    # Look for "The answer is X" pattern
    answer_is_match = re.search(r'(?:the\s+)?answer\s+is\s+([A-D])', response, re.IGNORECASE)
    if answer_is_match:
        return answer_is_match.group(1).upper()
    
    # Look for letter in parentheses like "(A)" at the end
    paren_match = re.search(r'\(([A-D])\)', response[-50:])
    if paren_match:
        return paren_match.group(1).upper()
    
    # Look for the last occurrence of a standalone letter in the last part of response
    end_section = response[-200:]  # Check last 200 characters
    letters = re.findall(r'\b([A-D])\b', end_section)
    if letters:
        return letters[-1].upper()
    
    # Look for any standalone letter in the full response (last resort)
    all_letters = re.findall(r'\b([A-D])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    # If nothing found, return A as default
    logging.warning("Could not parse answer from response, defaulting to A")
    return "A"