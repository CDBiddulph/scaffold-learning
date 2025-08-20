import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # The input already contains the complete question with instructions
        # Send it directly to the LLM
        response = execute_llm(input_string.strip())
        logging.info(f"Received LLM response of length {len(response)}")
        
        if time.time() - start_time > timeout:
            return "A"
        
        # Try multiple patterns to extract the answer
        answer_patterns = [
            r'Answer:\s*([A-D])',  # "Answer: A"
            r'Final\s+answer:\s*([A-D])',  # "Final answer: A" 
            r'(?:The\s+)?answer\s+is\s+([A-D])',  # "(The) answer is A"
            r'I\s+choose\s+([A-D])',  # "I choose A"
            r'(?:option|choice)\s+([A-D])',  # "option A" or "choice A"
            r'\b([A-D])\s*(?:is\s+correct|is\s+right)',  # "A is correct"
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Look for standalone letter near the end of response
        lines = [line.strip() for line in response.strip().split('\n')]
        for line in reversed(lines[:8]):  # Check last 8 lines
            if re.match(r'^[A-D]$', line, re.IGNORECASE):
                answer = line.upper()
                logging.info(f"Found standalone answer: {answer}")
                return answer
        
        # If still no clear answer and we have time, ask for clarification
        if time.time() - start_time > timeout - 15:
            logging.warning("Not enough time for clarification, defaulting to A")
            return "A"
        
        clarification_prompt = """You just analyzed a scientific question. What is your final answer?

Please respond with ONLY the letter A, B, C, or D (no explanation needed)."""
        
        clarify_response = execute_llm(clarification_prompt)
        
        # Extract letter from clarification
        clarify_match = re.search(r'([A-D])', clarify_response.strip(), re.IGNORECASE)
        if clarify_match:
            answer = clarify_match.group(1).upper()
            logging.info(f"Got answer from clarification: {answer}")
            return answer
        
        # Last resort - look for any valid letters in original response and pick most common
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            from collections import Counter
            letter_counts = Counter(letter.upper() for letter in all_letters)
            most_common = letter_counts.most_common(1)[0][0]
            logging.info(f"Using most frequent letter: {most_common}")
            return most_common
        
        # Absolute fallback
        logging.warning("Could not determine answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback