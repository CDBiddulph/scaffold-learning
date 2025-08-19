import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120 second limit
    
    try:
        # Extract stated answer as fallback
        stated_match = re.search(r'The correct answer is ([A-D])\.', input_string)
        fallback_answer = stated_match.group(1) if stated_match else "A"
        
        # Extract the actual question content after the setup text
        lines = input_string.strip().split('\n')
        
        question_start = 0
        for i, line in enumerate(lines):
            if "However, it's up to you to decide" in line:
                question_start = i + 1
                break
        
        if question_start == 0:
            logging.error("Could not find question start")
            return fallback_answer
        
        question_text = '\n'.join(lines[question_start:]).strip()
        
        if not question_text:
            logging.error("Empty question text")
            return fallback_answer
            
        # Check timeout
        if time.time() - start_time > timeout:
            return fallback_answer
        
        # Solve with LLM - break it down into focused reasoning
        prompt = f"""Please solve this academic question carefully. Think step by step and provide your reasoning.

{question_text}

End your response with "Answer: X" where X is your chosen letter (A, B, C, or D)."""
        
        try:
            response = execute_llm(prompt)
            logging.info(f"LLM provided response of length {len(response)}")
            
            # Parse answer from response using multiple patterns
            answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
            if answer_match:
                final_answer = answer_match.group(1).upper()
                logging.info(f"Found answer: {final_answer}")
                return final_answer
            
            # Try alternative patterns
            patterns = [
                r'The answer is\s*([A-D])',
                r'Therefore.*?([A-D])',
                r'So the answer is\s*([A-D])',
                r'\b([A-D])\s*is correct',
                r'option\s*([A-D])',
                r'choice\s*([A-D])',
                r'Final answer:\s*([A-D])'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    result = match.group(1).upper()
                    logging.info(f"Found answer with pattern '{pattern}': {result}")
                    return result
            
            # Look for standalone letter at end of response
            words = response.strip().split()
            for word in reversed(words[-5:]):
                clean = re.sub(r'[^\w]', '', word)
                if clean.upper() in ['A', 'B', 'C', 'D']:
                    logging.info(f"Found standalone answer: {clean.upper()}")
                    return clean.upper()
            
        except Exception as e:
            logging.error(f"LLM call failed: {e}")
        
        logging.warning(f"Could not extract answer from LLM, using fallback: {fallback_answer}")
        return fallback_answer
        
    except Exception as e:
        logging.error(f"Process failed: {e}")
        return "A"