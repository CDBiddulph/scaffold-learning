import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Clean up the input
        question = input_string.strip()
        
        # Create a clear prompt that emphasizes the expected format
        prompt = f"""You are answering a multiple choice question. Please think through this step-by-step and provide your final answer in the exact format requested.

{question}

Remember to end your response with "Answer: <letter>" where <letter> is A, B, C, or D."""

        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Get LLM response
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        logging.info(f"LLM response received: {response[:200]}...")
        
        # Parse the response to extract the answer
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract answer from LLM response, trying fallback")
            # Try a more direct approach
            fallback_answer = try_fallback_extraction(response)
            if fallback_answer:
                logging.info(f"Fallback extraction successful: {fallback_answer}")
                return fallback_answer
            else:
                logging.error("All parsing attempts failed, returning default answer A")
                return "A"
                
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback

def extract_answer(response: str) -> str:
    """Extract answer letter from LLM response using multiple strategies"""
    
    # Strategy 1: Look for "Answer: X" pattern (most direct)
    answer_pattern = r"Answer:\s*([ABCD])"
    match = re.search(answer_pattern, response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 2: Look for "final answer" or similar phrases followed by a letter
    final_patterns = [
        r"final answer.*?([ABCD])",
        r"the answer is.*?([ABCD])",
        r"correct answer.*?([ABCD])",
        r"answer.*?([ABCD])"
    ]
    
    for pattern in final_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look at the end of the response for standalone letters
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if len(line) == 1 and line.upper() in ['A', 'B', 'C', 'D']:
            return line.upper()
        
        # Check if line ends with a standalone letter
        words = line.split()
        if words and len(words[-1]) == 1 and words[-1].upper() in ['A', 'B', 'C', 'D']:
            return words[-1].upper()
    
    return None

def try_fallback_extraction(response: str) -> str:
    """More aggressive parsing when standard methods fail"""
    
    # Look for any occurrence of option letters in parentheses or after certain keywords
    patterns = [
        r"\(([ABCD])\)",
        r"option\s*([ABCD])",
        r"choice\s*([ABCD])",
        r"^([ABCD])\)",  # Line starting with letter and parenthesis
        r"([ABCD])$"     # Line ending with just a letter
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.MULTILINE | re.IGNORECASE)
        if matches:
            # Take the last match (most likely to be the final answer)
            return matches[-1].upper()
    
    # Count occurrences of each letter in the response as last resort
    counts = {}
    for letter in ['A', 'B', 'C', 'D']:
        counts[letter] = response.upper().count(letter)
    
    # Return the most frequently mentioned option (crude heuristic)
    if any(count > 0 for count in counts.values()):
        most_frequent = max(counts, key=counts.get)
        logging.warning(f"Using frequency-based fallback, selected {most_frequent}")
        return most_frequent
    
    return None