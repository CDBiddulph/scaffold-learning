import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """Process a multiple choice scientific question and return the answer letter."""
    
    question_text = input_string.strip()
    
    # Use the exact prompt format from the examples
    prompt = f"""{question_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
    
    try:
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Primary pattern: look for "Answer: X" format
        match = re.search(r'Answer:\s*([ABCD])\b', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer in expected format: {answer}")
            return answer
        
        # Secondary patterns for robustness
        backup_patterns = [
            r'answer\s+is\s+([ABCD])\b',
            r'correct\s+answer\s+is\s+([ABCD])\b',
            r'the\s+answer\s+is\s+([ABCD])\b',
            r'choose\s+([ABCD])\b',
            r'option\s+([ABCD])\b',
            r'select\s+([ABCD])\b'
        ]
        
        for pattern in backup_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using backup pattern '{pattern}': {answer}")
                return answer
        
        # Look for isolated letters at the end of lines (common in LLM responses)
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(lines[-3:]):  # Check last 3 lines
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found isolated answer letter: {line}")
                return line
        
        # Extract all valid answer letters and use the last occurrence
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last valid letter found: {answer}")
            return answer
        
        # If no answer found, log the response and return default
        logging.warning("No answer pattern found in response")
        logging.warning(f"Response excerpt: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"