import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing multiple choice question")
        
        # Check time limit early
        if time.time() - start_time > 110:
            logging.warning("Approaching time limit early")
            return "A"
            
        # Use the exact format shown in the examples
        prompt = f"""{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Check time limit after LLM call
        if time.time() - start_time > 115:
            logging.warning("Approaching time limit after LLM call")
            
        # Extract the answer letter using the expected format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
            
        # Backup extraction methods for common answer patterns
        backup_patterns = [
            r'(?:the answer is|answer is|final answer:?)\s*([A-D])',
            r'(?:option|choice)\s*([A-D])\s*is\s*correct',
            r'(?:correct answer:?|solution:?)\s*([A-D])',
            r'\b([A-D])\s*(?:is the correct|is correct)',
        ]
        
        for pattern in backup_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Backup pattern matched, answer: {answer}")
                return answer
        
        # Look for isolated letters near the end of the response
        final_section = response[-300:] if len(response) > 300 else response
        isolated_letters = re.findall(r'\b([A-D])\b', final_section)
        if isolated_letters:
            answer = isolated_letters[-1].upper()
            logging.info(f"Found isolated letter at end: {answer}")
            return answer
            
        # Final fallback - try to find any A-D in the response
        all_letters = re.findall(r'([A-D])', response, re.IGNORECASE)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Absolute fallback answer: {answer}")
            return answer
            
        logging.warning("Could not extract any answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        # Return a reasonable default
        return "A"