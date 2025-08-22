import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        lines = input_string.strip().split('\n')
        
        # Find the options A, B, C, D
        options = {}
        question_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Check for option patterns - handle both "A)" and "A " formats
            if re.match(r'^A[\)\s]', line):
                options['A'] = re.sub(r'^A[\)\s]\s*', '', line).strip()
            elif re.match(r'^B[\)\s]', line):
                options['B'] = re.sub(r'^B[\)\s]\s*', '', line).strip()
            elif re.match(r'^C[\)\s]', line):
                options['C'] = re.sub(r'^C[\)\s]\s*', '', line).strip()
            elif re.match(r'^D[\)\s]', line):
                options['D'] = re.sub(r'^D[\)\s]\s*', '', line).strip()
            else:
                # This is part of the question
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Parsed question: {question_text[:100]}...")
        logging.info(f"Found {len(options)} options")
        
        # Check time before making LLM call
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default answer")
            return 'A'
        
        # Create the prompt for the LLM
        prompt = f"""Please answer the following multiple choice question. Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".

{question_text}

A) {options.get('A', '')}
B) {options.get('B', '')}
C) {options.get('C', '')}
D) {options.get('D', '')}"""

        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        logging.info("Received response from LLM")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern first
        match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Look for final answer pattern like "The answer is X" or "The correct answer is X"
        match = re.search(r'(?:answer|correct)\s+is\s+([A-D])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer using 'answer is' pattern: {answer}")
            return answer
        
        # Look for the last occurrence of A, B, C, or D in the response
        answer_matches = re.findall(r'\b([A-D])\b', response)
        if answer_matches:
            answer = answer_matches[-1].upper()
            logging.info(f"Found answer using last letter pattern: {answer}")
            return answer
        
        # If still no match, return A as default
        logging.warning(f"Could not extract answer from response, using default")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return 'A'