import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    # Split by lines and find where the question starts
    lines = input_string.strip().split('\n')
    
    # Find the line that ends the validation function
    question_start_idx = 0
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            question_start_idx = i + 1
            break
    
    # Extract the question text
    question_lines = lines[question_start_idx:]
    question_text = '\n'.join(question_lines).strip()
    
    if not question_text:
        logging.error("Could not extract question text")
        return "A"
    
    logging.info(f"Extracted question (first 200 chars): {question_text[:200]}...")
    
    # Use LLM to solve the problem
    prompt = f"""You are an expert scientist with deep knowledge across multiple fields including physics, chemistry, astronomy, biology, and mathematics. Please solve this multiple choice question carefully.

{question_text}

Please think through this step by step, showing your reasoning clearly. Then provide your final answer in the exact format "Answer: <letter>" where <letter> is A, B, C, or D."""
    
    logging.info("Sending question to LLM for analysis")
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer from the response
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            # Fallback: look for various answer patterns
            fallback_patterns = [
                r'(?:the answer is|final answer is|therefore|thus|so|answer)\s*([A-D])',
                r'\b([A-D])\)',  # A), B), etc.
                r'option\s*([A-D])',
                r'choice\s*([A-D])',
                r'\b([A-D])\b'   # Just the letter as last resort
            ]
            
            for pattern in fallback_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                if matches:
                    answer = matches[-1].upper()
                    logging.info(f"Fallback pattern '{pattern}' matched: {answer}")
                    return answer
            
            logging.error("Could not extract answer from LLM response")
            logging.error(f"Response was: {response}")
            return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"  # Default fallback