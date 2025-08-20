import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Clean up the input
        input_text = input_string.strip()
        
        # The input format varies - some have A), some have A, some have different patterns
        # Let's find where the answer choices start by looking for lines that start with A, B, C, D
        lines = input_text.split('\n')
        
        question_lines = []
        choice_lines = []
        found_choices = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this looks like an answer choice
            if re.match(r'^[A-D][\)\s]', line) and not found_choices:
                found_choices = True
                choice_lines.append(line)
            elif found_choices:
                # Continue collecting choice lines
                if re.match(r'^[A-D][\)\s]', line):
                    choice_lines.append(line)
                else:
                    # This might be a continuation of a choice or instruction to ignore
                    if not re.search(r'Think step-by-step|final answer|format', line, re.IGNORECASE):
                        choice_lines.append(line)
            else:
                # This is part of the question
                if not re.search(r'Think step-by-step|final answer|format', line, re.IGNORECASE):
                    question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        choices = '\n'.join(choice_lines).strip()
        
        # Create comprehensive prompt
        full_text = f"{question}\n\n{choices}" if choices else question
        
        prompt = f"""You are solving a multiple choice scientific question. Analyze the problem step-by-step and determine the correct answer.

{full_text}

Please work through this systematically, explaining your reasoning, then conclude with "Answer: X" where X is the letter of the correct choice (A, B, C, or D)."""

        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching timeout")
            return "A"
        
        response = execute_llm(prompt)
        logging.info(f"Got LLM response of length {len(response)}")
        
        # Extract the answer with multiple patterns
        patterns = [
            r'Answer:\s*([A-D])',
            r'Final Answer:\s*([A-D])', 
            r'Answer:\s*<([A-D])>',
            r'The answer is\s*([A-D])',
            r'Therefore,?\s*([A-D])',
            r'So,?\s*([A-D])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # Fallback: get all single letter A-D occurrences and take the last one
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using fallback answer: {answer}")
            return answer
        
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"