import logging
import re
import time
from llm_executor import execute_llm

def extract_answer_letter(response):
    """Extract the final answer letter (A, B, C, or D) from LLM response"""
    # Look for explicit answer patterns first
    patterns = [
        r'Answer:\s*([ABCD])',
        r'answer\s*is\s*([ABCD])',
        r'correct\s*answer\s*is\s*([ABCD])',
        r'option\s*([ABCD])\s*is',
        r'choose\s*([ABCD])',
        r'select\s*([ABCD])',
        r'final\s*answer[:\s]*([ABCD])',
        r'the\s*([ABCD])\s*option',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Look for standalone letters at end of response
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Check if line starts with letter
        match = re.match(r'^([ABCD])[.)\s]', line)
        if match:
            return match.group(1)
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        question = input_string.strip()
        
        # Main prompt - asking for comprehensive analysis
        prompt = f"""You are an expert scientist with deep knowledge across multiple scientific domains including astronomy, chemistry, physics, biology, mathematics, and engineering.

Please solve this scientific question step by step:

{question}

Think through this systematically:
1. Carefully read and understand what the question is asking
2. Identify the relevant scientific principles and concepts
3. Analyze each multiple choice option
4. Apply any necessary calculations or reasoning
5. Determine which option is correct

Show your reasoning clearly and end your response with "Answer: X" where X is the correct letter (A, B, C, or D)."""

        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        logging.info("Received response from LLM")
        
        # Check for timeout
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default")
            return 'A'
        
        # Try to extract the answer
        answer = extract_answer_letter(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback if we couldn't extract the answer clearly
        if time.time() - start_time > 110:
            logging.warning("Timeout approaching, using emergency fallback")
            return 'A'
            
        logging.warning("Couldn't extract clear answer, using simple fallback prompt")
        
        simple_prompt = f"""Based on this scientific question, what is the correct answer? 
Respond with only the single letter A, B, C, or D - nothing else.

{question}"""
        
        simple_response = execute_llm(simple_prompt)
        logging.info("Received fallback response")
        
        simple_answer = extract_answer_letter(simple_response)
        
        if simple_answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Extracted answer from fallback: {simple_answer}")
            return simple_answer
            
        # Last resort - find any single A, B, C, or D in the response
        for char in simple_response.upper():
            if char in ['A', 'B', 'C', 'D']:
                logging.info(f"Found letter in response: {char}")
                return char
                
        logging.error("All extraction methods failed, using default")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return 'A'