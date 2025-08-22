import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check if this looks like a multiple choice question
        if not re.search(r'[A-D]\)', input_string):
            logging.warning("Input doesn't appear to contain multiple choice answers")
            return "A"
        
        # Use the LLM to analyze the question
        # I'll give it expertise across multiple scientific domains
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and related fields. Analyze the following multiple choice question carefully and determine the correct answer.

{input_string}

Think step by step to explain your reasoning, then write your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D.
"""
        
        # Check timeout before making LLM call
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)} characters")
        
        # Extract the final answer using multiple robust patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'answer:\s*([A-D])',
            r'Answer:\s*&lt;([A-D])&gt;',  # Handle HTML encoding
            r'final answer.*?([A-D])',
            r'the answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # Look for strong contextual indicators
        strong_patterns = [
            r'([A-D])\s*is\s*correct',
            r'([A-D])\s*is\s*the\s*correct\s*answer',
            r'choose\s*([A-D])',
            r'select\s*([A-D])',
            r'option\s*([A-D])\s*is'
        ]
        
        for pattern in strong_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Extracted answer using strong pattern: {answer}")
                return answer
        
        # Look for letters in concluding context
        conclusion_patterns = [
            r'(?:therefore|thus|so|hence),?\s*(?:the\s*answer\s*is\s*)?([A-D])',
            r'(?:consequently|in conclusion),?\s*([A-D])'
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Extracted answer using conclusion pattern: {answer}")
                return answer
        
        # Final fallback - find the last occurrence of any letter A-D
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        logging.warning("Could not extract any answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"