import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    logging.info(f"Processing input: {input_string[:100]}...")
    
    try:
        # Extract the question and answer choices
        lines = input_string.strip().split('\n')
        
        # Find the question part (everything before the answer choices)
        question_lines = []
        answer_choices = {}
        
        in_choices = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line is an answer choice
            choice_match = re.match(r'^([A-D])\)\s*(.*)', line)
            if choice_match:
                in_choices = True
                letter = choice_match.group(1)
                text = choice_match.group(2)
                answer_choices[letter] = text
            elif not in_choices:
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines)
        
        logging.info(f"Question: {question_text[:200]}...")
        logging.info(f"Answer choices: {list(answer_choices.keys())}")
        
        # Format the choices for the LLM
        choices_text = '\n'.join([f"{letter}) {text}" for letter, text in answer_choices.items()])
        
        # Create a prompt for the LLM to solve the problem
        prompt = f"""Please solve this multiple choice scientific question step by step. Use your knowledge of the relevant scientific principles, equations, and concepts.

Question:
{question_text}

Answer Choices:
{choices_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""
        
        # Check time remaining
        elapsed = time.time() - start_time
        if elapsed > 100:  # Leave buffer for timeout
            logging.warning("Approaching timeout, returning early")
            return "A"
        
        # Get the LLM response
        response = execute_llm(prompt)
        
        logging.info(f"LLM response: {response}")
        
        # Extract the answer letter from the response using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'answer:\s*([A-D])',
            r'final answer is\s*([A-D])',
            r'answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'([A-D])\s*is\s*(?:the\s*)?correct',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
            r'select\s*([A-D])',
            r'pick\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer_letter = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer_letter}")
                return answer_letter
        
        # If no explicit answer format found, look for the most recently mentioned letter
        letters_found = re.findall(r'\b([A-D])\b', response)
        if letters_found:
            answer_letter = letters_found[-1].upper()
            logging.info(f"Using last mentioned letter: {answer_letter}")
            return answer_letter
        
        # Look for answer choices mentioned in context
        for letter in ['A', 'B', 'C', 'D']:
            if f"option {letter}" in response.lower() or f"choice {letter}" in response.lower():
                logging.info(f"Found answer via option/choice reference: {letter}")
                return letter
        
        logging.error("Could not extract answer from LLM response")
        return "A"  # Default fallback
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback