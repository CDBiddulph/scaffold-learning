import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 20  # Leave 20 seconds buffer before timeout
    
    try:
        logging.info("Processing scientific multiple-choice question")
        
        # Check if we're approaching timeout
        if time.time() - start_time > 120 - timeout_buffer:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Prepare prompt for the LLM
        prompt = f"""You are an expert in multiple scientific domains including physics, chemistry, biology, astronomy, and mathematics. Please analyze this scientific question carefully.

{input_string.strip()}

Please follow these steps:
1. Identify the scientific domain and key concepts involved
2. Think through the problem systematically 
3. Consider each option carefully
4. Provide clear reasoning for your choice

End your response with your final answer in exactly this format:
Answer: <letter>

Where <letter> is A, B, C, or D."""

        # Get response from LLM
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract the answer letter using multiple strategies
        answer = extract_answer_letter(response)
        
        if answer:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract answer from LLM response")
            logging.warning(f"Response excerpt: {response[-200:]}")
            
            # Try a more direct approach if first attempt failed
            if time.time() - start_time < 120 - timeout_buffer:
                logging.info("Attempting direct question to LLM")
                direct_prompt = f"""What is the correct answer to this question? Respond with only the letter A, B, C, or D.

{input_string.strip()}"""
                
                direct_response = execute_llm(direct_prompt).strip()
                
                # Look for single letter response
                if len(direct_response) <= 3 and any(letter in direct_response.upper() for letter in ['A', 'B', 'C', 'D']):
                    for letter in ['A', 'B', 'C', 'D']:
                        if letter in direct_response.upper():
                            logging.info(f"Extracted answer from direct approach: {letter}")
                            return letter
            
            # Final fallback
            return "A"
            
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}", exc_info=True)
        return "A"

def extract_answer_letter(response):
    """Extract answer letter from LLM response using multiple strategies."""
    
    # Strategy 1: Look for exact "Answer: X" format
    answer_pattern = r'Answer:\s*([A-D])'
    matches = re.findall(answer_pattern, response, re.IGNORECASE)
    if matches:
        return matches[-1].upper()
    
    # Strategy 2: Look for common answer phrases
    answer_phrases = [
        r'the correct answer is\s*([A-D])',
        r'the answer is\s*([A-D])',
        r'I choose\s*([A-D])',
        r'I select\s*([A-D])',
        r'option\s*([A-D])',
        r'choice\s*([A-D])',
        r'letter\s*([A-D])',
    ]
    
    for pattern in answer_phrases:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Strategy 3: Look at the end of the response for isolated letters
    lines = response.strip().split('\n')
    for line in reversed(lines[-5:]):  # Check last 5 lines
        line = line.strip()
        # Look for lines that are just a letter or contain just a letter
        if len(line) <= 3:
            for letter in ['A', 'B', 'C', 'D']:
                if letter in line.upper():
                    return letter
    
    # Strategy 4: Look for parenthetical answers like "(A)" or "A)"
    paren_patterns = [
        r'\(([A-D])\)',
        r'([A-D])\)',
        r'\b([A-D])\b[.\s]*$'  # Letter at end of response
    ]
    
    for pattern in paren_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    return None