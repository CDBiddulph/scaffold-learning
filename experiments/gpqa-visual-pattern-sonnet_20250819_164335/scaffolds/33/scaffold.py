import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave 10 seconds buffer
    
    try:
        # Clean up the input by removing any special symbols that might interfere
        input_clean = re.sub(r'■\s*', '', input_string)
        
        # Parse the input to extract question and choices
        lines = input_clean.strip().split('\n')
        
        # Find the answer choices (lines starting with A), B), C), D))
        choices = {}
        question_lines = []
        choices_started = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line is an answer choice
            choice_match = re.match(r'^([ABCD])\)\s*(.+)', line)
            if choice_match:
                choices_started = True
                choice_letter = choice_match.group(1)
                choice_text = choice_match.group(2).strip()
                choices[choice_letter] = choice_text
            elif not choices_started:
                question_lines.append(line)
        
        if not choices or len(choices) != 4:
            logging.error(f"Could not find 4 answer choices. Found: {choices}")
            return "A"  # Default fallback
        
        question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Parsed question (first 100 chars): {question_text[:100]}...")
        logging.info(f"Found choices: {list(choices.keys())}")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create prompt for LLM
        prompt = f"""You are answering a multiple choice question from a scientific/technical exam. These questions require deep technical knowledge and careful analysis.

{question_text}

A) {choices.get('A', '')}
B) {choices.get('B', '')}
C) {choices.get('C', '')}
D) {choices.get('D', '')}

Please think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""

        logging.info("Calling LLM to solve the question")
        response = execute_llm(prompt)
        
        logging.info(f"LLM response (first 300 chars): {response[:300]}...")
        
        # Extract the final answer from the response
        final_answer = None
        
        # Try to find "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer pattern: {final_answer}")
        else:
            # Fallback: look for other common answer patterns
            patterns = [
                r'final answer is\s*([ABCD])',
                r'answer is\s*([ABCD])', 
                r'correct answer is\s*([ABCD])',
                r'\b([ABCD])\s*is the correct',
                r'choose\s*([ABCD])',
                r'option\s*([ABCD])'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    final_answer = match.group(1).upper()
                    logging.info(f"Found answer with pattern '{pattern}': {final_answer}")
                    break
            
            # Last resort: look for the last occurrence of a single letter A, B, C, or D
            if not final_answer:
                letters = re.findall(r'\b([ABCD])\b', response)
                if letters:
                    final_answer = letters[-1].upper()
                    logging.info(f"Found letter fallback: {final_answer}")
        
        if final_answer and final_answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Returning answer: {final_answer}")
            return final_answer
        else:
            logging.warning(f"Could not extract valid answer from response, defaulting to A")
            return "A"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback