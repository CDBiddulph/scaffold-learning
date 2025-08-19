import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse input to skip validation function and extract the actual question
        lines = input_string.strip().split('\n')
        
        # Skip the validation function lines (first 3 lines typically)
        question_start = 0
        for i, line in enumerate(lines):
            if not (line.strip().startswith('#') or 
                   line.strip().startswith('def') or 
                   line.strip().startswith('return') or 
                   not line.strip()):
                question_start = i
                break
        
        # Extract the scientific question
        question_text = '\n'.join(lines[question_start:])
        logging.info(f"Extracted question (first 200 chars): {question_text[:200]}...")
        
        # Check timeout early to avoid issues
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Construct prompt for the LLM
        prompt = f"""You are an expert in multiple scientific fields. Solve this scientific multiple choice question using your knowledge and reasoning abilities.

{question_text}

Work through this problem systematically:
1. Identify what scientific principles apply
2. Set up any necessary equations or relationships  
3. Perform calculations if needed
4. Evaluate the answer choices
5. Select the best answer

Provide your final answer in the exact format: Answer: <letter>"""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer: {result}")
            return result
        
        # Fallback: look for pattern with parentheses like "(A)" or similar
        paren_match = re.search(r'\(([ABCD])\)', response)
        if paren_match:
            result = paren_match.group(1).upper()
            logging.info(f"Found answer in parentheses: {result}")
            return result
        
        # Another fallback: find the last clear letter choice mentioned
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using last letter found: {result}")
            return result
            
        # Final fallback
        logging.warning("Could not extract clear answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"