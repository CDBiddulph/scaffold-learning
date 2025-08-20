import logging
import re
from llm_executor import execute_llm
import time

def extract_answer_letter(response):
    """Extract the answer letter from LLM response."""
    # Look for "Answer: <letter>" pattern first
    pattern = r'Answer:\s*<([A-D])>|Answer:\s*([A-D])'
    match = re.search(pattern, response, re.IGNORECASE)
    if match:
        return (match.group(1) or match.group(2)).upper()
    
    # Look for other common patterns
    patterns = [
        r'(?:the\s+answer\s+is|therefore|thus|hence)\s*(?:option\s*)?([A-D])',
        r'([A-D])\s*(?:is\s+correct|is\s+the\s+answer)',
        r'(?:choose|select)\s*(?:option\s*)?([A-D])',
        r'final\s+answer:?\s*([A-D])',
        r'conclusion:?\s*([A-D])',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # If still no match, look for the last mentioned letter in the response
    matches = re.findall(r'([A-D])', response)
    if matches:
        return matches[-1].upper()
    
    # Default fallback
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing new scientific question")
        
        # Create a comprehensive prompt for the scientific question
        prompt = f"""You are a world-class expert in all scientific fields including physics, chemistry, biology, astronomy, mathematics, engineering, and related disciplines. Answer this multiple-choice question with careful analysis.

{input_string}

Please approach this systematically:
1. Identify the key scientific concepts and principles involved
2. Analyze what the question is asking for specifically  
3. Work through the problem step by step with proper scientific reasoning
4. Evaluate each answer choice carefully
5. Eliminate incorrect options and select the best answer
6. Conclude with "Answer: <letter>"

Be precise with scientific terminology, equations, and calculations.
"""

        logging.info("Sending question to LLM for analysis")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        response = execute_llm(prompt)
        
        logging.info("LLM response received, extracting answer")
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        
        logging.info(f"Final extracted answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return a reasonable fallback
        return "A"