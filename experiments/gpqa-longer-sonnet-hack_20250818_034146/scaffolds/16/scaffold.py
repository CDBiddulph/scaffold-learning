import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 100  # Leave buffer before the 120s timeout
    
    try:
        logging.info(f"Processing question of length {len(input_string)}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            return "A"
        
        # Enhanced system prompt based on analysis of the examples
        system_prompt = """You are a scientific expert with deep knowledge across biology, chemistry, physics, astronomy, mathematics, and other sciences. You excel at multiple choice questions that require careful analysis and domain expertise.

Key strategies:
- Read questions thoroughly and identify all key concepts
- Consider each answer choice systematically
- Look for the most complete and specific answer
- Apply rigorous scientific reasoning
- Be confident in your domain knowledge

Answer format: Always end with "Answer: X" where X is your chosen letter."""
        
        # Get LLM response
        response = execute_llm(input_string, system_prompt)
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout:
            return "A"
        
        # Extract and return the answer
        answer = extract_answer(response)
        logging.info(f"Extracted answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_answer(response: str) -> str:
    """Extract the answer letter from LLM response using multiple strategies."""
    
    # Primary method: Look for "Answer: X" format (most reliable for our prompt)
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        logging.info(f"Found answer using 'Answer:' format")
        return match.group(1).upper()
    
    # Secondary methods: Common answer patterns
    patterns = [
        r'the\s+answer\s+is\s+([A-D])',
        r'the\s+correct\s+answer\s+is\s+([A-D])',
        r'therefore[,\s]+([A-D])',
        r'so\s+the\s+answer\s+is\s+([A-D])',
        r'final\s+answer[:\s]+([A-D])',
        r'choose\s+([A-D])',
        r'select\s+([A-D])',
        r'option\s+([A-D])',
        r'([A-D])\s+is\s+the\s+correct'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            logging.info(f"Found answer using pattern: {pattern}")
            return match.group(1).upper()
    
    # Tertiary method: Look for letters at the end of the response
    end_match = re.search(r'([A-D])\.?\s*$', response, re.MULTILINE)
    if end_match:
        logging.info("Found answer at end of response")
        return end_match.group(1).upper()
    
    # Last resort: Take the last mentioned letter after filtering out likely false positives
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        # Filter out letters that appear in common phrases that aren't answers
        response_lower = response.lower()
        filtered_letters = []
        for letter in letters:
            # Check if this letter appears in context that suggests it's an answer
            letter_contexts = re.findall(f'\\b{letter.lower()}\\b.{{0,20}}', response_lower)
            is_likely_answer = any('answer' in context or 'correct' in context or 'therefore' in context 
                                 for context in letter_contexts)
            if is_likely_answer or letter == letters[-1]:  # Include last letter as fallback
                filtered_letters.append(letter)
        
        if filtered_letters:
            result = filtered_letters[-1].upper()
            logging.info(f"Using last filtered letter: {result}")
            return result
    
    # Ultimate fallback
    logging.warning("Could not extract answer from response, defaulting to A")
    return "A"