import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing multiple choice question")
    
    try:
        # The input already contains instructions for format, so pass it directly
        response = execute_llm(input_string)
        logging.info("Received LLM response")
        
        # Extract the answer letter
        answer_letter = extract_answer_letter(response)
        
        if answer_letter:
            logging.info(f"Successfully extracted answer: {answer_letter}")
            return answer_letter
        else:
            logging.warning("Could not extract answer, trying more direct approach")
            # More direct prompt if extraction failed
            direct_prompt = f"{input_string}\n\nIMPORTANT: End your response with exactly 'Answer: X' where X is A, B, C, or D."
            direct_response = execute_llm(direct_prompt)
            
            answer_letter = extract_answer_letter(direct_response)
            if answer_letter:
                return answer_letter
            else:
                logging.error("Could not extract answer from any response")
                return "A"  # Fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"

def extract_answer_letter(response: str) -> str:
    """Extract answer letter from LLM response with multiple strategies"""
    
    # Strategy 1: Look for "Answer: X" format (primary expected format)
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Strategy 2: Look for other common answer formats
    patterns = [
        r'final\s+answer\s+is\s*([A-D])',
        r'the\s+answer\s+is\s*([A-D])',  
        r'correct\s+answer\s+is\s*([A-D])',
        r'choose\s*([A-D])',
        r'option\s*([A-D])',
        r'letter\s*([A-D])'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Strategy 3: Look at the end of the response for a standalone letter
    lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
    for line in reversed(lines[-3:]):  # Check last 3 non-empty lines
        if len(line) <= 5:  # Very short lines likely to be just an answer
            match = re.search(r'^([A-D])$', line, re.IGNORECASE)
            if match:
                return match.group(1).upper()
    
    # Strategy 4: Find any letter A-D in the last part of the response
    last_part = response[-300:]  # Last 300 chars
    matches = re.findall(r'\b([A-D])\b', last_part)
    if matches:
        return matches[-1].upper()  # Return the last occurrence
    
    return None