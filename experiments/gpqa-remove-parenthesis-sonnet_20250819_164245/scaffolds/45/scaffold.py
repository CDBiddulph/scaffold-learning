import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Pass the question directly to the LLM - it already contains proper instructions
        response = execute_llm(input_string.strip())
        logging.info("LLM response received")
        
        # Extract the final answer using multiple methods for robustness
        
        # Method 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Method 2: Look for "Answer X" without colon
        answer_match = re.search(r'Answer\s+([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer via 'Answer' pattern: {answer}")
            return answer
        
        # Method 3: Look for common final answer patterns
        answer_match = re.search(r'(?:the\s+answer\s+is|final\s+answer:\s*|therefore[,\s]+)([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer via final answer pattern: {answer}")
            return answer
        
        # Method 4: Get the last isolated letter in the response
        letters = re.findall(r'\b([A-D])\b', response.upper())
        if letters:
            answer = letters[-1]
            logging.info(f"Extracted answer via last letter method: {answer}")
            return answer
        
        # If all methods fail, log the response and return default
        logging.error("Could not extract answer from LLM response")
        logging.error(f"Response preview: {response[:300]}...")
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"