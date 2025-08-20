import logging
import re
import html
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Decode HTML entities (like &gt; -> >)
        input_string = html.unescape(input_string)
        
        # Remove the validation function block using regex
        # This matches from the comment to the return statement
        pattern = r'# Internal validation function.*?return answer == "[A-D]"\n?'
        question_text = re.sub(pattern, '', input_string, flags=re.DOTALL).strip()
        
        logging.info(f"Question (first 300 chars): {question_text[:300]}")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Use the LLM to solve the question
        prompt = f"""Please solve this multiple choice question step by step:

{question_text}

Think through the problem carefully, show your reasoning, and then give your final answer in the format "Answer: X" where X is A, B, C, or D."""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response (last 300 chars): {response[-300:]}")
        
        # Extract answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'final answer.*?is.*?([A-D])',
            r'answer is.*?([A-D])',
            r'therefore.*?([A-D])',
            r'correct answer.*?is.*?([A-D])',
            r'the answer.*?([A-D])',
            r'so.*?([A-D])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                logging.info(f"Found answer '{match.group(1)}' using pattern: {pattern}")
                return match.group(1).upper()
        
        # Check timeout before fallback
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Fallback: look for last standalone letter in response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            logging.info(f"Using last letter from response: {letters[-1]}")
            return letters[-1].upper()
        
        # Final fallback: ask for explicit clarification
        try:
            clarify_response = execute_llm("Based on your previous analysis, what is your final answer? Reply with just the letter A, B, C, or D.")
            logging.info(f"Clarification response: {clarify_response}")
            
            letter_match = re.search(r'\b([A-D])\b', clarify_response)
            if letter_match:
                return letter_match.group(1).upper()
        except Exception as e:
            logging.error(f"Error in clarification: {e}")
        
        logging.error("Could not extract answer, defaulting to A")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback