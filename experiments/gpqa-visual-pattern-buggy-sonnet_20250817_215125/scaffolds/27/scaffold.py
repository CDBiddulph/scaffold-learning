import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second timeout
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        system_prompt = ("You are answering multiple choice questions. Always end your response with "
                        "'Answer: X' where X is the letter of your choice (A, B, C, or D).")
        
        logging.info("Sending question to LLM")
        response = execute_llm(input_string.strip(), system_prompt=system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Primary method: Look for "Answer: <letter>" pattern
        answer_pattern = r"Answer:\s*([A-D])"
        match = re.search(answer_pattern, response, re.IGNORECASE)
        
        if match:
            answer_letter = match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer_letter}")
            return answer_letter
        
        # Fallback methods if primary pattern fails
        logging.warning("Could not find 'Answer: X' pattern, trying fallback methods")
        
        # Try multiple fallback patterns in order of reliability
        fallback_patterns = [
            r"(?:the answer is|therefore|thus|hence)\s*([A-D])",  # "The answer is A"
            r"(?:option|choice)\s*([A-D])",  # "Option A"
            r"^([A-D])\s*$",  # Just letter on own line
            r"\b([A-D])\)\s*[A-Z~]",  # "A) Something" format
        ]
        
        for i, pattern in enumerate(fallback_patterns):
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer_letter = matches[-1].upper()  # Take last match
                logging.info(f"Fallback method {i+1} extracted answer: {answer_letter}")
                return answer_letter
        
        # Last resort: find any standalone A, B, C, or D
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            # Filter out letters that appear in common words
            filtered_letters = []
            for letter in all_letters:
                # Simple heuristic: if it's not surrounded by lowercase letters, it's likely an answer
                if not re.search(rf'[a-z]{letter.lower()}[a-z]', response, re.IGNORECASE):
                    filtered_letters.append(letter)
            
            if filtered_letters:
                answer_letter = filtered_letters[-1].upper()
                logging.info(f"Last resort extracted answer: {answer_letter}")
                return answer_letter
        
        logging.error("Could not extract any valid answer from response")
        logging.error(f"Response was: {response[:500]}...")  # Log first 500 chars for debugging
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback