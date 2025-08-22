import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Handle HTML entities and parse input
        text = input_string.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        lines = text.strip().split('\n')
        
        # Find where metadata ends
        content_start = 0
        for i, line in enumerate(lines):
            if '</question-metadata>' in line:
                content_start = i + 1
                break
        
        # Extract question text and choices
        question_parts = []
        choices = {}
        
        for i in range(content_start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
                
            # Check if this is a multiple choice option
            choice_match = re.match(r'^([A-D])\)\s*(.*)', line)
            if choice_match:
                letter, text = choice_match.groups()
                choices[letter] = text.strip()
                continue
            
            # Stop at the instruction line
            if any(phrase in line.lower() for phrase in [
                'think step-by-step', 
                'final answer in the format', 
                'write your final answer'
            ]):
                break
                
            # Otherwise, add to question
            question_parts.append(line)
        
        question_text = '\n'.join(question_parts).strip()
        
        # Validate we have what we need
        if not question_text:
            logging.error("Could not extract question text")
            return "A"
            
        if len(choices) < 4:
            logging.error(f"Only found {len(choices)} choices, expected 4")
            return "A"
        
        # Check if we're approaching timeout
        if time.time() - start_time > 100:  # Leave 20s buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Format the choices properly
        formatted_choices = []
        for letter in ['A', 'B', 'C', 'D']:
            if letter in choices:
                formatted_choices.append(f"{letter}) {choices[letter]}")
        
        choices_text = '\n'.join(formatted_choices)
        
        # Create a focused prompt for the LLM
        prompt = f"""Please solve this academic question step by step.

Question:
{question_text}

Answer choices:
{choices_text}

Think through this carefully and provide your final answer as "ANSWER: X" where X is the correct letter (A, B, C, or D)."""

        logging.info(f"Solving question: {question_text[:100]}...")
        
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Try multiple patterns to extract the answer
        answer_patterns = [
            r'ANSWER:\s*([A-D])',
            r'Answer:\s*([A-D])', 
            r'Final answer:\s*([A-D])',
            r'The correct answer is\s*([A-D])',
            r'The answer is\s*([A-D])',
            r'Therefore,?\s*([A-D])',
            r'^([A-D])$',  # Single letter on its own line
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                if answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Successfully extracted answer: {answer}")
                    return answer
        
        # Fallback: look for any A, B, C, D in the response and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using fallback answer: {answer}")
            return answer
            
        # Ultimate fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback