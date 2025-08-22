import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Create prompt that follows the example format shown in instructions
        prompt = f"""Answer this multiple choice question. Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".

{input_string}"""

        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:200]}...")
        
        # Look for "Answer: X" pattern first (matches expected format)
        answer_match = re.search(r'Answer\s*:\s*([A-D])\b', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer in expected format: {result}")
            return result
        
        # Fallback patterns if the LLM doesn't follow exact format
        patterns = [
            r'(?:FINAL ANSWER|ANSWER|CHOICE|LETTER)\s*:?\s*([A-D])\b',
            r'\b([A-D])\s*(?:IS|WOULD BE|CORRECT)',
            r'(?:^|\W)([A-D])(?:\W|$)'
        ]
        
        response_upper = response.upper()
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, response_upper)
            if match:
                result = match.group(1)
                logging.info(f"Found answer using fallback pattern {i}: {result}")
                return result
        
        # Final fallback - just look for any A, B, C, D in the response
        for letter in ['A', 'B', 'C', 'D']:
            if letter in response_upper:
                logging.warning(f"Using final fallback, found letter: {letter}")
                return letter
        
        logging.warning(f"Could not extract any answer from response: {response[:200]}...")
        return 'A'  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return 'A'  # Safe fallback