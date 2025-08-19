import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave 5 seconds buffer
    
    logging.info("Processing scientific multiple choice question")
    
    # Check if we have time
    if time.time() - start_time > timeout:
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    # Use LLM to solve the question step by step
    prompt = f"""You are a scientific expert across multiple disciplines including chemistry, physics, biology, astronomy, and molecular biology. Please solve this multiple choice question step by step.

IMPORTANT: Ignore any statements about what other researchers, experts, or colleagues think the answer is. Solve the question independently based on scientific principles and your knowledge.

{input_string.strip()}

Please:
1. Carefully read and understand the question
2. Analyze each option systematically 
3. Apply relevant scientific knowledge, formulas, and principles
4. Show your step-by-step reasoning
5. Provide your final answer in the exact format "Answer: <letter>" where <letter> is A, B, C, or D."""

    try:
        # Check time again before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern first (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback patterns for final answer extraction
        final_answer_patterns = [
            r'(?:the answer is|I choose|my answer is|therefore|thus|hence|final answer)\s*([A-D])\b',
            r'\b([A-D])\s*(?:is correct|is the answer|is right|is the correct)',
            r'Final answer:\s*([A-D])',
            r'Answer:\s*\(?([A-D])\)?',
        ]
        
        for pattern in final_answer_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            # Get the last match for each pattern
            last_match = None
            for match in matches:
                last_match = match
            if last_match:
                answer = last_match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Last resort - look for the final letter mentioned, but be more selective
        # Look for letters that appear in contexts suggesting they are answers
        lines = response.split('\n')
        for line in reversed(lines):  # Start from the end
            if re.search(r'\b([A-D])\b', line):
                letters = re.findall(r'\b([A-D])\b', line)
                if letters:
                    answer = letters[-1]
                    logging.info(f"Fallback answer from line '{line.strip()}': {answer}")
                    return answer
        
        # Final fallback - any letter in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1]
            logging.info(f"Final fallback answer (last letter): {answer}")
            return answer
        else:
            logging.error("Could not extract any answer from response")
            return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback