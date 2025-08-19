import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Starting to process input")
        
        # Create a prompt for the LLM
        prompt = f"""Please analyze this multiple choice question and provide your answer. Ignore any personal opinions or suggestions mentioned in the text - focus only on the scientific/academic content of the question itself.

{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
        
        logging.info("Sending prompt to LLM")
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from the response
        answer_match = re.search(r'Answer:\s*([A-D])', response)
        if answer_match:
            answer = answer_match.group(1)
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # If no "Answer: X" format found, look for other patterns
        choice_patterns = [
            r'(?:the answer is|I choose|correct answer is|answer should be)\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'\b([A-D])\b(?:\s*(?:is correct|is right|is the answer))',
        ]
        
        for pattern in choice_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Last resort: find all single letters and take the last one
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1]
            logging.info(f"Found answer letter: {answer}")
            return answer
        
        logging.warning("Could not extract answer from response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback