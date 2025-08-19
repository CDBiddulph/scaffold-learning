import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before the 120s timeout
    
    try:
        # Extract the actual question by removing the validation function
        lines = input_string.strip().split('\n')
        
        # Find where the validation function ends
        question_start_idx = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                question_start_idx = i + 1
                break
        
        # Join the remaining lines to form the question
        question_lines = lines[question_start_idx:]
        question = '\n'.join(question_lines).strip()
        
        if not question:
            logging.error("No question found after parsing")
            return "A"
        
        logging.info(f"Extracted question (first 300 chars): {question[:300]}")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning early")
            return "A"
        
        # Use a specialized system prompt for scientific problems
        system_prompt = (
            "You are solving advanced scientific problems across physics, chemistry, biology, "
            "and astronomy. These are graduate-level questions requiring careful analysis. "
            "Work through each problem systematically by identifying key principles, setting up "
            "equations when needed, and performing calculations step by step. "
            "Pay close attention to units, molecular structures, and physical relationships. "
            "Always conclude with 'Answer: X' where X is the correct letter choice."
        )
        
        response = execute_llm(question, system_prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer from the response using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (case insensitive)
        answer_pattern = r"Answer:\s*([A-D])"
        match = re.search(answer_pattern, response, re.IGNORECASE)
        
        if match:
            answer = match.group(1).upper()
            logging.info(f"Extracted answer using Answer: pattern: {answer}")
            return answer
        
        # Strategy 2: Look for alternative answer patterns
        alternative_patterns = [
            r'(?:final\s+)?answer\s*(?:is|:)\s*([A-D])',
            r'(?:the\s+)?correct\s+(?:answer|choice|option)\s*(?:is|:)\s*([A-D])',
            r'(?:therefore|thus|hence),?\s*(?:the\s+)?answer\s*(?:is|:)?\s*([A-D])',
            r'(?:so\s+)?(?:the\s+)?answer\s+(?:must\s+)?be\s+([A-D])',
        ]
        
        for pattern in alternative_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern {pattern}: {answer}")
                return answer
        
        # Strategy 3: Look at the last few lines for standalone letters
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):
            line = line.strip()
            if re.match(r'^[A-D]\)?\.?$', line):
                answer = line[0].upper()
                logging.info(f"Found standalone answer letter: {answer}")
                return answer
        
        # Strategy 4: Look for letters in parentheses at the end of sentences
        final_sentence_pattern = r'\b([A-D])\)?\s*\.?\s*$'
        match = re.search(final_sentence_pattern, response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer at end of sentence: {answer}")
            return answer
        
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        logging.warning(f"Response was: {response[-200:]}")  # Log last 200 chars for debugging
        return "A"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback