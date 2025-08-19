import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_choices(input_string):
    """Extract the question text and answer choices from the input."""
    # Remove the ■ symbols and HTML entities
    cleaned_input = input_string.replace('■', '').replace('&lt;', '<').replace('&gt;', '>')
    
    lines = cleaned_input.strip().split('\n')
    
    # Find the instruction line to know where to stop
    instruction_idx = -1
    for i, line in enumerate(lines):
        if 'Think step-by-step' in line:
            instruction_idx = i
            break
    
    if instruction_idx > 0:
        lines = lines[:instruction_idx]
    
    # Find where the choices start
    question_lines = []
    choices = {}
    choice_pattern = re.compile(r'^\s*([ABCD])\s*[\)\]\s]*\s*(.*)', re.IGNORECASE)
    
    in_choices = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        choice_match = choice_pattern.match(line)
        if choice_match:
            in_choices = True
            letter = choice_match.group(1).upper()
            text = choice_match.group(2).strip()
            choices[letter] = text
        elif not in_choices:
            # This is part of the question
            question_lines.append(line)
    
    question = ' '.join(question_lines).strip()
    return question, choices

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before the 120 second limit
    
    try:
        # Extract question and choices
        question, choices = extract_question_and_choices(input_string)
        
        if not question or len(choices) < 2:
            logging.error(f"Failed to extract question or choices properly. Question length: {len(question)}, Choices: {len(choices)}")
            return "A"  # Default fallback
        
        logging.info(f"Extracted question: {question[:200]}...")
        logging.info(f"Choices: {list(choices.keys())}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Format the prompt for the LLM
        prompt = f"""You are answering a multiple choice question. Analyze the question carefully and provide your reasoning.

Question: {question}

Answer choices:
"""
        
        for letter in ['A', 'B', 'C', 'D']:
            if letter in choices:
                prompt += f"{letter}) {choices[letter]}\n"
        
        prompt += "\nThink step-by-step to explain your reasoning, then write your final answer in the format \"Answer: <letter>\"."

        # Get LLM response
        logging.info("Calling LLM...")
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback 1: look for "The answer is X" or "The correct answer is X"
        answer_match = re.search(r'(?:the\s+(?:correct\s+)?answer\s+is\s+)([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Fallback 1 answer extraction: {answer}")
            return answer
            
        # Fallback 2: look for the last occurrence of a single letter A, B, C, or D
        single_letter_matches = re.findall(r'\b([ABCD])\b', response)
        if single_letter_matches:
            answer = single_letter_matches[-1]
            logging.info(f"Fallback 2 answer extraction: {answer}")
            return answer
        
        # Fallback 3: Try a second, more direct prompt
        if time.time() - start_time < timeout - 20:  # If we have time for another call
            simple_prompt = f"""Question: {question}

{chr(10).join([f'{letter}) {choices[letter]}' for letter in ['A', 'B', 'C', 'D'] if letter in choices])}

Answer with only the letter (A, B, C, or D):"""
            
            simple_response = execute_llm(simple_prompt)
            simple_answer_match = re.search(r'\b([ABCD])\b', simple_response)
            if simple_answer_match:
                answer = simple_answer_match.group(1).upper()
                logging.info(f"Simple prompt answer extraction: {answer}")
                return answer
        
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback