import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 100  # Leave some buffer before the 120s limit
    
    try:
        # Parse the input to extract the actual question
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts by skipping validation function
        question_lines = []
        skip_mode = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip validation function and comments
            if stripped.startswith('# Internal validation function') or stripped.startswith('def validate_answer'):
                skip_mode = True
                continue
            elif skip_mode and (stripped.startswith('return ') or stripped == ''):
                if stripped.startswith('return '):
                    skip_mode = False
                continue
            elif skip_mode:
                continue
            else:
                # This is part of the actual question
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Prompt the LLM to solve the question step by step
        prompt = f"""You are answering a multiple choice question. Please analyze it carefully and think step-by-step to solve it, then provide your final answer.

{question_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Check timeout again
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout after LLM call, returning default answer")
            return "A"
        
        # Extract the answer letter from the response using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using pattern matching: {result}")
            return result
        
        # Strategy 2: Look for the last occurrence of A), B), C), or D) in the response
        choice_matches = re.findall(r'\b([A-D])\)', response)
        if choice_matches:
            result = choice_matches[-1].upper()
            logging.info(f"Found answer using choice pattern: {result}")
            return result
        
        # Strategy 3: Look for standalone letters near the end of response
        lines = response.split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            letter_match = re.search(r'\b([A-D])\b', line)
            if letter_match:
                result = letter_match.group(1).upper()
                logging.info(f"Found answer using standalone letter: {result}")
                return result
        
        # Strategy 4: Final fallback - any letter in the response
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            result = letter_matches[-1].upper()
            logging.info(f"Found answer using any letter fallback: {result}")
            return result
        
        logging.error(f"Could not extract answer from response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback