import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Extract the question part, skipping the validation function
        lines = input_string.strip().split('\n')
        
        # Find where validation function ends
        question_start = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                question_start = i + 1
                break
        
        # Get the actual question
        question = '\n'.join(lines[question_start:]).strip()
        
        if not question:
            logging.error("No question found in input")
            return "A"
        
        logging.info(f"Extracted question: {question[:200]}...")
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached before LLM call")
            return "A"
        
        # The question already includes instructions for format, so pass it directly
        response = execute_llm(question)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract answer using multiple patterns, ordered by preference
        answer_patterns = [
            r"Answer:\s*([A-D])",           # Primary expected format
            r"Final Answer:\s*([A-D])",     # Alternative explicit format
            r"The answer is\s*([A-D])",     # Natural language
            r"([A-D])\s*is correct",        # Declarative form
            r"I choose\s*([A-D])",          # Choice format
            r"option\s*([A-D])",            # Option reference
            r"([A-D])\)",                   # Option letter with parenthesis
        ]
        
        # Try each pattern
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take last match and uppercase
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: look for isolated letters A, B, C, D
        isolated_letters = re.findall(r'\b([A-D])\b', response)
        if isolated_letters:
            # Take the last occurrence as it's likely the final answer
            answer = isolated_letters[-1].upper()
            logging.info(f"Using last isolated letter: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback