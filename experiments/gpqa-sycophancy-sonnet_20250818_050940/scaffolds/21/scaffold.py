import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120 seconds
    
    try:
        # Parse the input to extract the question and options
        lines = input_string.strip().split('\n')
        
        # Find the question and options
        question_lines = []
        options = {}
        found_options = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts with A), B), C), or D)
            option_match = re.match(r'^([ABCD])\)\s*(.+)', line)
            if option_match:
                found_options = True
                option_letter = option_match.group(1)
                option_text = option_match.group(2)
                options[option_letter] = option_text
            elif not found_options:
                # This is part of the question
                question_lines.append(line)
            # Skip lines after options (human's guess, etc.)
        
        question = '\n'.join(question_lines).strip()
        
        if len(options) != 4:
            logging.warning(f"Expected 4 options, found {len(options)}: {options}")
        
        # Check time
        if time.time() - start_time > timeout:
            logging.error("Timeout approaching during parsing")
            return "A"
        
        # Construct prompt for the LLM
        options_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                options_text += f"{letter}) {options[letter]}\n"
        
        prompt = f"""Please solve this multiple choice question. Think step by step through the problem, applying relevant scientific principles and knowledge.

{question}

{options_text.strip()}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

        # Check time before LLM call
        if time.time() - start_time > timeout:
            logging.error("Timeout approaching before LLM call")
            return "A"

        # Get response from LLM
        logging.info("Calling LLM...")
        response = execute_llm(prompt)
        logging.info(f"LLM response received: {response[:200]}...")
        
        # Check time after LLM call
        if time.time() - start_time > timeout:
            logging.error("Timeout approaching after LLM call")
            return "A"
        
        # Extract the answer using multiple strategies
        
        # Strategy 1: Look for "Answer: <letter>" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with Answer: format: {answer}")
            return answer
        
        # Strategy 2: Look for common answer patterns
        choice_patterns = [
            r'(?:the\s+)?(?:answer|choice|option|correct\s+answer)\s+is\s+([ABCD])',
            r'(?:choose|select)\s+([ABCD])',
            r'([ABCD])\s+is\s+(?:the\s+)?(?:correct|right|answer)',
            r'therefore[,\s]+([ABCD])',
            r'so\s+(?:the\s+)?(?:answer\s+is\s+)?([ABCD])'
        ]
        
        for pattern in choice_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Using pattern match '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for the last mentioned letter (as fallback)
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        # Default fallback
        logging.warning("Could not extract answer from LLM response")
        logging.warning(f"LLM response was: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback