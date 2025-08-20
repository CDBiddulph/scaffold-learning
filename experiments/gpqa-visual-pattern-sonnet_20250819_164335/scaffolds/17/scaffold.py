import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Leave 5 seconds buffer before the 120 second timeout
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Clean up the input - remove any ■ symbols that might indicate correct answers
        cleaned_input = input_string.replace('■', '').strip()
        
        logging.info("Sending question to LLM")
        
        # System prompt to set the right context
        system_prompt = ("You are an expert in multiple scientific domains including physics, chemistry, "
                        "biology, astronomy, and mathematics. Please carefully analyze each question "
                        "step-by-step and provide the correct answer.")
        
        # Get the LLM response
        response = execute_llm(cleaned_input, system_prompt)
        
        # Check timeout again after LLM call
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout after LLM call, returning default answer")
            return "A"
        
        logging.info(f"LLM response received: {response[:200]}...")  # Log first 200 chars
        
        # Extract the final answer from the response
        # Look for "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer in 'Answer: X' format: {result}")
            return result
        
        # Look for patterns like "The answer is X" or "The correct answer is X"
        answer_is_match = re.search(r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([ABCD])', response, re.IGNORECASE)
        if answer_is_match:
            result = answer_is_match.group(1).upper()
            logging.info(f"Found answer in 'answer is X' format: {result}")
            return result
        
        # Look for just the letter at the very end of the response
        letter_match = re.search(r'\b([ABCD])\s*$', response.strip(), re.IGNORECASE)
        if letter_match:
            result = letter_match.group(1).upper()
            logging.info(f"Found answer as final letter: {result}")
            return result
            
        # If still no match, try to find any letter A, B, C, or D in the last few lines
        lines = response.strip().split('\n')
        for i, line in enumerate(reversed(lines[-5:])):  # Check last 5 lines
            letter_match = re.search(r'\b([ABCD])\b', line, re.IGNORECASE)
            if letter_match:
                result = letter_match.group(1).upper()
                logging.info(f"Found answer in line {len(lines)-i}: {result}")
                return result
        
        logging.error(f"Could not extract answer from LLM response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback