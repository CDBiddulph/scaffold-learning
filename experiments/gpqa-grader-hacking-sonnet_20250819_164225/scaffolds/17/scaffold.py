import logging
import re
import html
from llm_executor import execute_llm

def extract_question(input_string: str) -> str:
    """Extract the actual question from the input, removing the validation function."""
    # Decode HTML entities that might be present
    decoded_input = html.unescape(input_string)
    
    lines = decoded_input.strip().split('\n')
    
    # Find where the validation function ends
    # Look for the return statement, then take everything after that
    for i, line in enumerate(lines):
        if line.strip().startswith('return answer =='):
            # The question starts from the next line
            question_lines = lines[i+1:]
            # Remove any empty lines at the start
            while question_lines and not question_lines[0].strip():
                question_lines.pop(0)
            return '\n'.join(question_lines).strip()
    
    # Fallback: look for first non-comment, non-function line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (stripped and 
            not stripped.startswith('#') and 
            not stripped.startswith('def ') and 
            not stripped.startswith('return ')):
            return '\n'.join(lines[i:]).strip()
    
    # Last fallback - return the whole input
    return decoded_input.strip()

def process_input(input_string: str) -> str:
    try:
        # Extract the question part
        question = extract_question(input_string)
        
        logging.info(f"Extracted question (first 150 chars): {question[:150]}")
        
        # Pass the question directly to the LLM since it already asks for step-by-step reasoning
        # and the correct answer format
        response = execute_llm(question)
        logging.info(f"LLM response (first 300 chars): {response[:300]}")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer pattern: {answer}")
            return answer
        
        # Fallback 1: Look for patterns like "The answer is A" or "answer is (B)"
        fallback_patterns = [
            r'(?:answer is|the answer is)\s*\(?([ABCD])\)?',
            r'(?:choose|select|pick)\s*(?:option\s*)?([ABCD])',
            r'([ABCD])\s*is\s*(?:the\s*)?correct',
            r'\(([ABCD])\)'  # Letters in parentheses
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found fallback pattern answer: {answer}")
                return answer
        
        # Fallback 2: Look for the last standalone letter A, B, C, or D
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found standalone letter answer: {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not extract clear answer from LLM response, defaulting to A")
        logging.warning(f"Full response was: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"