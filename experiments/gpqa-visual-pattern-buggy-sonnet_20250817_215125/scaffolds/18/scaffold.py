import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 110  # Leave buffer before 120s timeout
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where the uppercase options start (A) B) C) D))
        question_lines = []
        options = []
        
        # Look for uppercase options with potential ■ symbol
        option_pattern = r'^[■\s]*([A-D])\)'
        found_options = False
        
        for line in lines:
            if re.match(option_pattern, line):
                # This is an option line
                found_options = True
                match = re.match(r'^[■\s]*([A-D])\)\s*(.*)', line)
                if match:
                    option_letter = match.group(1)
                    option_text = match.group(2)
                    options.append(f"{option_letter}) {option_text}")
            elif not found_options:
                # This is part of the question (only collect lines before options start)
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        if not options:
            logging.error("No options found in input")
            return "A"
        
        if len(options) != 4:
            logging.warning(f"Expected 4 options, found {len(options)}")
        
        logging.info(f"Parsed question length: {len(question)} chars")
        logging.info(f"Found {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > max_time:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
        
        # Create prompt for LLM
        prompt = f"""{question}

{chr(10).join(options)}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""

        system_prompt = """You are an expert in multiple academic disciplines including chemistry, physics, biology, astronomy, mathematics, computer science, and more. 

Solve this multiple choice question by:
1. Reading the question carefully
2. Considering each option 
3. Using your knowledge to reason through the problem step by step
4. Selecting the best answer

IMPORTANT: Always end your response with exactly "Answer: X" where X is A, B, C, or D."""
        
        # Get response from LLM
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # Extract the answer from the response
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Multiple fallback patterns
        answer_patterns = [
            r'answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'final answer:\s*([A-D])',
            r'choose\s*([A-D])',
            r'option\s*([A-D])',
            r'the answer:\s*([A-D])',
            r'select\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Fallback answer using pattern '{pattern}': {answer}")
                return answer
        
        # Last resort: look for standalone letters in the final lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last few lines
            line = line.strip()
            # Look for patterns like "A.", "(A)", "A)", etc.
            letter_patterns = [
                r'\b([A-D])\.',
                r'\(([A-D])\)',
                r'\b([A-D])\)',
                r'^([A-D])$',
                r'\b([A-D])\b'
            ]
            
            for pattern in letter_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    answer = matches[-1].upper()
                    logging.info(f"Last resort answer from line '{line}': {answer}")
                    return answer
        
        logging.warning("Could not extract answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback