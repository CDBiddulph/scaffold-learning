import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check if we're running out of time (leave 20 second buffer)
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Send the question directly to the LLM since it's already well-formatted
        # with step-by-step instructions
        response = execute_llm(input_string)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Primary pattern: look for "Answer: X" format as requested in the questions
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using primary pattern: {answer}")
            return answer
        
        # Fallback patterns in case the LLM doesn't follow exact format
        fallback_patterns = [
            r'([A-D])\)',  # A)
            r'\(([A-D])\)',  # (A)
            r'answer\s+is\s+([A-D])',  # "answer is A"
            r'correct\s+answer\s+is\s+([A-D])',  # "correct answer is A"  
            r'\b([A-D])\b(?=[^A-D]*$)',  # Last occurrence of A-D in text
        ]
        
        for i, pattern in enumerate(fallback_patterns):
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using fallback pattern {i+1}: {answer}")
                return answer
        
        # If no pattern matches, log the response for debugging
        logging.error(f"Could not extract answer from response. First 300 chars: {response[:300]}...")
        
        # Final fallback - just return A
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback