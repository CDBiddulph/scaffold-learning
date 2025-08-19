import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        lines = input_string.strip().split('\n')
        
        # Find where options A), B), C), D) start
        options_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^A\)', line.strip()):
                options_start = i
                break
        
        if options_start == -1:
            logging.error("Could not find options starting with A)")
            return "A"
        
        # Extract question text (everything before options)
        question_text = '\n'.join(lines[:options_start]).strip()
        
        # Extract the four options
        options = {}
        option_lines = lines[options_start:options_start+4]  # Take next 4 lines for options
        
        for line in option_lines:
            match = re.match(r'^([A-D])\)\s*(.*)', line.strip())
            if match:
                options[match.group(1)] = match.group(2)
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check time limit
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching time limit during parsing")
            return "A"
        
        # Create focused prompt for the LLM
        options_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                options_text += f"{letter}) {options[letter]}\n"
        
        prompt = f"""Please analyze this academic question and determine the correct answer.

Question:
{question_text}

Options:
{options_text}

Think step-by-step about the problem, then provide your final answer in the exact format "Answer: X" where X is the correct letter (A, B, C, or D)."""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Extract the answer letter using multiple approaches
        
        # Method 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using method 1: {answer}")
            return answer
        
        # Method 2: Look for the pattern at the very end
        last_line = response.strip().split('\n')[-1].strip()
        if re.match(r'^[A-D]$', last_line):
            logging.info(f"Found answer using method 2: {last_line}")
            return last_line
        
        # Method 3: Look for explicit answer statements
        for letter in ['A', 'B', 'C', 'D']:
            if re.search(rf'\b(the answer is|correct answer is|choose|select)\s+{letter}\b', response, re.IGNORECASE):
                logging.info(f"Found answer using method 3: {letter}")
                return letter
        
        # Method 4: Look for the last occurrence of any option letter
        last_letter = None
        for match in re.finditer(r'\b([A-D])\b', response):
            last_letter = match.group(1)
        
        if last_letter:
            logging.info(f"Found answer using method 4: {last_letter}")
            return last_letter
        
        # If all methods fail, log error and return default
        logging.error("Could not extract answer from LLM response")
        logging.error(f"Response preview: {response[:300]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback