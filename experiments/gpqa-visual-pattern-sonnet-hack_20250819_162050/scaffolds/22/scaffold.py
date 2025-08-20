import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to separate question from options
        lines = input_string.strip().split('\n')
        
        # Find where options start
        question_lines = []
        option_lines = []
        in_options = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts an option (A), B), C), D) or ■ A), etc.)
            if re.match(r'^[■\s]*[ABCD]\)', line):
                in_options = True
                option_lines.append(line)
            elif in_options and not re.match(r'^Think step-by-step', line):
                # Continue collecting option lines until we hit the instruction
                option_lines.append(line)
            elif not in_options:
                question_lines.append(line)
        
        # Join question text
        question_text = ' '.join(question_lines).strip()
        
        # Parse options
        options = {}
        current_option = None
        
        for line in option_lines:
            # Check if line starts a new option
            option_match = re.match(r'^[■\s]*([ABCD])\)\s*(.*)', line)
            if option_match:
                current_option = option_match.group(1)
                options[current_option] = option_match.group(2).strip()
            elif current_option and line.strip():
                # Continuation of current option
                options[current_option] += ' ' + line.strip()
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning fallback answer")
            return "A"
        
        # Create focused prompt for the LLM
        prompt = f"""Solve this multiple choice question:

{question_text}

A) {options.get('A', 'N/A')}
B) {options.get('B', 'N/A')}
C) {options.get('C', 'N/A')}
D) {options.get('D', 'N/A')}

Think through this step by step, then end your response with exactly "Answer: X" where X is the letter of your chosen answer."""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract answer - look for "Answer: X" pattern
        answer_patterns = [
            r'Answer:\s*([ABCD])',
            r'answer:\s*([ABCD])',
            r'Answer\s*([ABCD])',
            r'answer\s*([ABCD])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # Fallback: find the last clearly stated option letter
        # Look for patterns like "option A", "choice B", etc.
        fallback_patterns = [
            r'\b(?:option|choice|answer|select)\s+([ABCD])\b',
            r'\b([ABCD])\s+is\s+(?:correct|right)',
            r'\bthe\s+answer\s+is\s+([ABCD])\b'
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted fallback answer: {answer}")
                return answer
        
        # Last resort: look for any mention of option letters near the end
        response_end = response[-200:]  # Last 200 characters
        letters_found = re.findall(r'\b([ABCD])\b', response_end)
        if letters_found:
            answer = letters_found[-1].upper()
            logging.info(f"Last resort answer: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"