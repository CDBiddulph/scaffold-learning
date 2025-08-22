import logging
import re
import html
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the question text from the input, removing the validation function."""
    # Decode HTML entities
    decoded = html.unescape(input_string)
    
    # Split by lines and find where the actual question starts
    lines = decoded.split('\n')
    
    # Find the line with "return answer ==" and take everything after it
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            question_text = '\n'.join(lines[i+1:]).strip()
            # Remove leading quote if present
            if question_text.startswith('"'):
                question_text = question_text[1:]
            return question_text
    
    # Fallback: if no validation function found, return the entire input
    logging.warning("Could not find validation function, using entire input")
    return decoded.strip()

def process_input(input_string: str) -> str:
    """Process the input and return the correct multiple choice answer."""
    try:
        # Extract the question part (excluding validation function)
        question_text = extract_question_and_options(input_string)
        
        logging.info(f"Extracted question length: {len(question_text)} characters")
        
        # The question text already contains the instruction format, so pass it directly to LLM
        response = execute_llm(question_text)
        
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Extract the answer using the expected format "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback 1: Look for "The answer is X" or similar patterns
        fallback_patterns = [
            r'(?:the )?(?:correct )?answer is\s*([ABCD])',
            r'(?:option|choice)\s*([ABCD])\s*is\s*correct',
            r'therefore[,\s]*([ABCD])',
            r'so[,\s]*([ABCD])'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using fallback pattern: {answer}")
                return answer
        
        # Fallback 2: Look for the last occurrence of A, B, C, or D in the response
        letters = re.findall(r'\b([ABCD])\b', response.upper())
        if letters:
            answer = letters[-1]
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        # Final fallback: return A as default
        logging.warning("Could not extract clear answer from LLM response, defaulting to A")
        logging.warning(f"Response was: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        logging.error(f"Input was: {input_string[:200]}...")
        return "A"