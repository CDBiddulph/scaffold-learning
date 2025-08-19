import logging
import re
import time
from llm_executor import execute_llm

def parse_question(input_string):
    """Parse the question and extract answer choices"""
    lines = input_string.strip().split('\n')
    
    question_lines = []
    answer_choices = {}
    in_choices = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts with A), B), C), or D)
        choice_match = re.match(r'^([ABCD])\)\s*(.*)', line)
        if choice_match:
            in_choices = True
            choice_letter = choice_match.group(1)
            choice_text = choice_match.group(2)
            answer_choices[choice_letter] = choice_text
        elif not in_choices:
            # Skip instructional text like "Think step-by-step..."
            if not line.startswith("Think step-by-step"):
                question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    return question_text, answer_choices

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120s timeout
    
    try:
        # Parse the question and answer choices
        question_text, answer_choices = parse_question(input_string)
        
        if not question_text or len(answer_choices) < 2:
            logging.error("Failed to parse question or insufficient answer choices")
            return "A"
        
        logging.info(f"Question length: {len(question_text)} chars, {len(answer_choices)} choices")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Format the complete problem for the LLM
        choices_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in answer_choices:
                choices_text += f"{letter}) {answer_choices[letter]}\n"
        
        # Create a comprehensive prompt
        prompt = f"""{question_text}

{choices_text.strip()}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
        
        # Get LLM response
        response = execute_llm(prompt)
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout after LLM call")
            return "A"
        
        logging.info(f"Got LLM response ({len(response)} chars)")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            if final_answer in answer_choices:
                logging.info(f"Found answer via 'Answer:' pattern: {final_answer}")
                return final_answer
        
        # Strategy 2: Look for conclusive statements
        conclusive_patterns = [
            r'(?:the\s+(?:correct\s+)?answer\s+is|therefore\s*,?\s*(?:the\s+answer\s+is\s*)?|thus\s*,?\s*|hence\s*,?\s*)\s*(?:option\s*)?([ABCD])',
            r'([ABCD])\s+is\s+(?:the\s+)?correct',
            r'option\s*([ABCD])\s+is\s+correct',
            r'(?:choose|select)\s+(?:option\s*)?([ABCD])',
        ]
        
        for pattern in conclusive_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                letter = match.upper()
                if letter in answer_choices:
                    logging.info(f"Found answer via pattern '{pattern}': {letter}")
                    return letter
        
        # Strategy 3: Look for the last mentioned valid choice
        all_letters = re.findall(r'\b([ABCD])\b', response)
        valid_letters = [l.upper() for l in all_letters if l.upper() in answer_choices]
        
        if valid_letters:
            final_answer = valid_letters[-1]
            logging.info(f"Using last mentioned valid choice: {final_answer}")
            return final_answer
        
        # Strategy 4: Fallback - return first available choice
        available_choices = sorted(answer_choices.keys())
        if available_choices:
            logging.warning("No answer found, using first available choice")
            return available_choices[0]
        
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"