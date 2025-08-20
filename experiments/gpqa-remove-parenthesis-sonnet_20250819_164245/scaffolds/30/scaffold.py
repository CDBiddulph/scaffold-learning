import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120 second limit
    
    try:
        logging.info(f"Processing input: {input_string[:200]}...")
        
        # Check if input already has step-by-step instructions
        has_instructions = any(phrase in input_string.lower() for phrase in [
            "step-by-step", "think step", "explain your reasoning"
        ])
        
        if has_instructions:
            # Input already has good instructions, use as-is
            prompt = input_string
        else:
            # Add step-by-step instructions
            prompt = f"""{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""
        
        # Check timeout before calling LLM
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use the LLM to solve the problem
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        logging.info(f"LLM response end: {response[-200:]}")
        
        # Extract the answer using multiple strategies
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Last resort: return A
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_answer(response):
    """Extract the answer letter from LLM response using multiple strategies."""
    
    # Strategy 1: Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for "Answer: <X>" pattern  
    answer_match = re.search(r'Answer:\s*<([ABCD])>', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 3: Look for "Answer: &lt;X&gt;" (HTML encoded)
    answer_match = re.search(r'Answer:\s*&lt;([ABCD])&gt;', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 4: Look in the last part of the response for common patterns
    end_text = response[-300:]  
    
    patterns = [
        r'final answer.*?([ABCD])',
        r'answer.*?is.*?([ABCD])',
        r'answer.*?([ABCD])',
        r'therefore.*?([ABCD])',
        r'thus.*?([ABCD])',
        r'so.*?([ABCD])',
        r'\b([ABCD])\)',  # "A)" format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, end_text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 5: Look for isolated letters at the very end
    last_100 = response[-100:]
    isolated_letters = re.findall(r'\b([ABCD])\b', last_100)
    if isolated_letters:
        return isolated_letters[-1].upper()  # Return the last one found
    
    # Strategy 6: Look for any letter in the response (very last resort)
    all_letters = re.findall(r'([ABCD])', response, re.IGNORECASE)
    if all_letters:
        # Return the most common letter, or if tied, the last one
        from collections import Counter
        letter_counts = Counter(letter.upper() for letter in all_letters)
        return letter_counts.most_common(1)[0][0]
    
    return None