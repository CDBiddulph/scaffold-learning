import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing multiple choice question")
        
        # Send the input directly to the LLM since it already contains the question,
        # options, and instruction for step-by-step reasoning
        response = execute_llm(input_string.strip())
        
        logging.info(f"LLM response received: {response[:300]}...")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first (most specific to the instruction)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer_letter = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer: X' pattern: {answer_letter}")
            return answer_letter
        
        # Look for other common answer patterns if the main one isn't found
        patterns = [
            r'final answer is\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'my answer is\s*([A-D])',
            r'I choose\s*([A-D])',
            r'option\s*([A-D])\s*is\s*correct',
            r'correct answer is\s*([A-D])',
            r'([A-D])\s*is\s*the\s*correct\s*answer',
            r'([A-D])\s*is\s*correct',
            r'select\s*([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer_letter = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer_letter}")
                return answer_letter
        
        # If no specific pattern matched, look for the last option letter mentioned
        # This handles cases where the LLM might conclude with something like "Therefore, C."
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer_letter = letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer_letter}")
            return answer_letter
        
        # Absolute fallback if no letters found at all
        logging.warning("No answer letter found in response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe fallback to prevent crashes