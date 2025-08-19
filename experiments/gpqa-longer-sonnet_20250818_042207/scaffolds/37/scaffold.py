import logging
import re
from llm_executor import execute_llm

def extract_answer(response: str) -> str:
    """Extract the answer letter from LLM response using multiple strategies."""
    
    # Strategy 1: Look for "Answer: <letter>" pattern (most specific)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "The answer is <letter>" or similar patterns
    answer_match = re.search(r'(?:the\s+answer\s+is|final\s+answer\s+is|answer\s*:?)\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 3: Look for the last occurrence of a single letter A-D in the final sentences
    sentences = response.split('.')
    for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
        letters = re.findall(r'\b([A-D])\b', sentence, re.IGNORECASE)
        if letters:
            return letters[-1].upper()
    
    # Strategy 4: Look for the very last occurrence of a single letter A-D
    letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
    if letters:
        return letters[-1].upper()
    
    # Strategy 5: Look for letter followed by closing parenthesis
    match = re.search(r'([A-D])\)', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return None

def process_input(input_string: str) -> str:
    try:
        # The input already contains instructions for the LLM to follow
        # Pass it directly to get step-by-step reasoning and final answer
        response = execute_llm(input_string)
        logging.info(f"LLM response received, length: {len(response)}")
        
        answer = extract_answer(response)
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        logging.error(f"Could not extract answer from response. First 500 chars: {response[:500]}")
        # Try one more time with a more direct prompt
        fallback_prompt = f"{input_string}\n\nPlease provide only the letter of your final answer (A, B, C, or D):"
        fallback_response = execute_llm(fallback_prompt)
        
        fallback_answer = extract_answer(fallback_response)
        if fallback_answer:
            logging.info(f"Fallback extracted answer: {fallback_answer}")
            return fallback_answer
            
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback