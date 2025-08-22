import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 100  # Leave buffer before 120s limit
    
    try:
        # Extract the question part (everything before "Think step-by-step...")
        question_match = re.search(r'^(.*?)Think step-by-step', input_string, re.DOTALL)
        if question_match:
            question_text = question_match.group(1).strip()
        else:
            question_text = input_string.strip()
        
        logging.info(f"Processing question of {len(question_text)} characters")
        
        # Check timeout early
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Create expert-level prompt optimized for scientific questions
        prompt = f"""You are a world-renowned expert scientist with deep knowledge across all scientific disciplines including:
- Chemistry (organic, inorganic, analytical, physical)
- Physics (classical, quantum, relativity, thermodynamics)
- Biology (molecular, genetics, biochemistry, microbiology)
- Astronomy and astrophysics
- Mathematics and engineering

Analyze this multiple-choice question with scientific rigor:

{question_text}

Approach systematically:
1. Identify the core scientific principles involved
2. Perform any calculations needed
3. Apply relevant theories, laws, or experimental knowledge
4. Eliminate incorrect options through logical reasoning
5. Select the most scientifically accurate answer

Provide your final answer as: Answer: X (where X is A, B, C, or D)
"""
        
        # Execute with remaining time check
        if time.time() - start_time > timeout:
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"Got LLM response of {len(response)} characters")
        
        # Extract answer letter with multiple fallback methods
        answer = extract_answer_letter(response)
        logging.info(f"Extracted answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback

def extract_answer_letter(response):
    """Extract answer letter using multiple strategies"""
    
    # Strategy 1: Look for explicit "Answer: X" format
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Strategy 2: Look for conclusion phrases with letters
    conclusion_patterns = [
        r'final answer.*?([ABCD])',
        r'answer is.*?([ABCD])', 
        r'correct answer.*?([ABCD])',
        r'therefore.*?([ABCD])',
        r'hence.*?([ABCD])',
        r'thus.*?([ABCD])'
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look for letters in the final portion of response
    final_section = response[-300:]  # Last 300 characters most likely to contain answer
    letter_matches = re.findall(r'\b([ABCD])\b', final_section)
    if letter_matches:
        return letter_matches[-1].upper()  # Take the last occurrence
    
    # Strategy 4: Look for parenthetical answers like "(C)" or "option C"
    paren_match = re.search(r'[(\[]([ABCD])[)\]]', response)
    if paren_match:
        return paren_match.group(1).upper()
        
    option_match = re.search(r'option\s+([ABCD])', response, re.IGNORECASE)
    if option_match:
        return option_match.group(1).upper()
    
    # Strategy 5: Last resort - any letter in the response
    all_letters = re.findall(r'\b([ABCD])\b', response)
    if all_letters:
        return all_letters[-1].upper()
    
    # Ultimate fallback
    logging.warning(f"Could not extract answer from response: {response[:200]}...")
    return "A"