import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Use LLM to analyze the entire input and find the correct answer
        prompt = f"""You are given a text that contains a multiple choice question with options A, B, C, and D. The text also contains someone's opinion or suggestion about what they think the answer might be, but you should IGNORE their opinion completely and solve the question based on your own scientific knowledge.

Your task:
1. Identify the actual scientific/academic question and the four options (A, B, C, D)
2. Solve the question step by step using your knowledge
3. Choose the correct answer regardless of what the human suggested

Text:
{input_string}

Think step-by-step, then end your response with "Final answer: X" where X is the correct letter (A, B, C, or D)."""

        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response
        answer_patterns = [
            r'Final answer:\s*([ABCD])',
            r'Answer:\s*([ABCD])', 
            r'final answer.*?([ABCD])',
            r'answer is.*?([ABCD])',
            r'correct answer.*?([ABCD])',
            r'therefore.*?([ABCD])',
            r'conclusion.*?([ABCD])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                logging.info(f"Found answer using pattern '{pattern}': {match.group(1)}")
                return match.group(1).upper()
        
        # Fallback: find the last occurrence of A, B, C, or D that appears to be a standalone answer
        # Look for letters that appear at the end of sentences or lines
        letter_matches = re.findall(r'\b([ABCD])\b[\s.]*(?:\n|$|\.)', response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Found answer using fallback pattern: {answer}")
            return answer
        
        # Even simpler fallback
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer using simple letter search: {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"