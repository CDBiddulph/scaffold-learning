import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input
        lines = input_string.strip().split('\n')
        
        # Find the "Think step-by-step" instruction line to separate content from instructions
        instruction_idx = -1
        for i, line in enumerate(lines):
            if 'Think step-by-step' in line:
                instruction_idx = i
                break
        
        # Use all lines if no instruction found, otherwise use lines before instruction
        content_lines = lines if instruction_idx == -1 else lines[:instruction_idx]
        
        # Parse question and options
        question_lines = []
        options = {}
        current_option = None
        
        for line in content_lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new option (handle ■ symbol marking correct answer)
            option_match = re.match(r'^[■]*\s*([ABCD])\)\s*(.*)', line)
            if option_match:
                current_option = option_match.group(1)
                option_text = option_match.group(2)
                options[current_option] = option_text
            elif current_option:
                # This line continues the current option
                options[current_option] += ' ' + line
            else:
                # This line is part of the question
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        logging.info(f"Parsed question: {question[:100]}...")
        logging.info(f"Parsed options: {list(options.keys())}")
        
        # Check timeout before making LLM call
        if time.time() - start_time > 110:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Ensure we have all four options
        for letter in ['A', 'B', 'C', 'D']:
            if letter not in options:
                options[letter] = 'Not provided'
        
        # Format the prompt for the LLM
        prompt = f"""Question: {question}

Options:
A) {options['A']}
B) {options['B']}
C) {options['C']}
D) {options['D']}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""

        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:200]}...")
        
        # Extract the answer from the response - look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback 1: Look for final answer pattern at end of response
        final_answer_match = re.search(r'(?:final answer|answer).*?([ABCD])', response, re.IGNORECASE)
        if final_answer_match:
            answer = final_answer_match.group(1).upper()
            logging.info(f"Extracted final answer: {answer}")
            return answer
        
        # Fallback 2: Look for the last occurrence of A, B, C, or D in the response
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Fallback answer (last letter): {answer}")
            return answer
            
        # If no clear answer found, log error and return default
        logging.error(f"Could not extract answer from LLM response: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"