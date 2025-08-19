import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Give ourselves a buffer before the 120 second timeout
    
    try:
        # Parse the question and options
        lines = input_string.strip().split('\n')
        
        # Find the options (lines starting with A), B), C), D) or ■ A), ■ B), etc.)
        option_pattern = r'^(?:■\s*)?([ABCD])\)\s*(.+)$'
        options = {}
        question_lines = []
        
        for line in lines:
            match = re.match(option_pattern, line)
            if match:
                letter, text = match.groups()
                options[letter] = text
            else:
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Format the question for the LLM
        formatted_question = question_text + '\n\n'
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                formatted_question += f"{letter}) {options[letter]}\n"
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
        
        # Ask the LLM to solve it
        prompt = (
            "You are solving advanced academic multiple choice questions from various fields including "
            "chemistry, physics, astronomy, biology, mathematics, materials science, and more.\n\n"
            
            "Please solve the following question by:\n"
            "1. First identifying what academic field/topic this question covers\n"
            "2. Recalling the relevant principles, equations, or concepts\n"
            "3. Working through the problem step by step\n"
            "4. Evaluating each option to determine which is correct\n"
            "5. Providing your final answer\n\n"
            
            f"{formatted_question}\n\n"
            
            "Think step-by-step to explain your reasoning, then write your final answer in the format \"Answer: <letter>\""
        )
        
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response
        answer_pattern = r'Answer:\s*([ABCD])'
        match = re.search(answer_pattern, response, re.IGNORECASE)
        
        if match:
            answer = match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        else:
            # Try to find the answer in other formats
            fallback_patterns = [
                r'(?:The answer is|Answer is|Final answer:)\s*([ABCD])',
                r'(?:Therefore|Thus|So),?\s*(?:the\s+)?answer\s+is\s*([ABCD])',
                r'\b([ABCD])\s*is\s+(?:the\s+)?correct',
                r'correct\s+answer\s+is\s*([ABCD])',
                r'(?:^|\n)([ABCD])\s*$'
            ]
            
            for pattern in fallback_patterns:
                match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
                if match:
                    answer = match.group(1).upper()
                    logging.info(f"Extracted answer using fallback pattern: {answer}")
                    return answer
            
            logging.error(f"Could not extract answer from response: {response}")
            return "A"  # Default fallback
            
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback