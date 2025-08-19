import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120 second limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Parse input to extract question and options
        lines = input_string.strip().split('\n')
        
        # Find where options start (look for line starting with "A)")
        option_start_idx = None
        for i, line in enumerate(lines):
            if re.match(r'^\s*A\)', line.strip()):
                option_start_idx = i
                break
        
        if option_start_idx is None:
            logging.error("Could not find option A) in input")
            return "A"
        
        # Everything before options is the question
        question_lines = lines[:option_start_idx]
        question = '\n'.join(question_lines).strip()
        
        # Extract options A) B) C) D)
        options = {}
        for i in range(option_start_idx, min(option_start_idx + 10, len(lines))):
            line = lines[i].strip()
            match = re.match(r'^([A-D])\)\s*(.+)$', line)
            if match:
                letter = match.group(1)
                content = match.group(2) 
                options[letter] = content
                
        logging.info(f"Extracted question with {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout")
            return "A"
        
        # Format options for the prompt
        formatted_options = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                formatted_options += f"{letter}) {options[letter]}\n"
        
        # Create focused prompt for step-by-step scientific reasoning
        prompt = f"""Solve this scientific multiple choice question step by step.

QUESTION:
{question}

OPTIONS:
{formatted_options.strip()}

Please:
1. Identify what scientific concepts and principles apply
2. Set up the problem with relevant equations/formulas if needed
3. Work through the solution systematically
4. Evaluate each option to determine which is correct

Conclude with: "Answer: X" where X is the correct letter (A, B, C, or D)."""

        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout before LLM call")
            return "A"
            
        logging.info("Sending to LLM for analysis")
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {result}")
            return result
        
        # Strategy 2: Look for conclusive statements
        conclusion_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'(?:therefore|thus|hence),?\s+([A-D])',
            r'option\s+([A-D])\s+is\s+(?:correct|right)',
            r'(?:choose|select)\s+([A-D])',
            r'([A-D])\s+is\s+the\s+correct'
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer via conclusion pattern: {result}")
                return result
        
        # Strategy 3: Look for isolated letter in final lines
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-5:]):
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found isolated answer letter: {line}")
                return line
        
        # Strategy 4: Find last occurrence of A, B, C, or D
        for char in reversed(response):
            if char in 'ABCD':
                logging.warning(f"Using last occurrence fallback: {char}")
                return char
        
        logging.error("Could not extract answer from LLM response")
        logging.error(f"Response preview: {response[:300]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"