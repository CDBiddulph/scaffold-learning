import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s limit
    
    try:
        # Parse the input to extract question and options
        lines = input_string.strip().split('\n')
        
        # Skip validation function and find the actual question
        question_lines = []
        options = {}
        found_question_start = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip the validation function
            if line.startswith('def validate_answer') or line.startswith('    return'):
                continue
                
            # Check for option format: A) text, B) text, etc.
            option_match = re.match(r'^([A-D])\)\s*(.+)$', line)
            if option_match:
                found_question_start = True
                letter = option_match.group(1)
                content = option_match.group(2)
                options[letter] = content
            elif not any(letter in options for letter in ['A', 'B', 'C', 'D']) or not found_question_start:
                # This is part of the question
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        logging.info(f"Question extracted: {question[:150]}...")
        logging.info(f"Options: {list(options.keys())}")
        
        if time.time() - start_time > timeout:
            return "A"
        
        # Create a comprehensive prompt for scientific analysis
        options_text = '\n'.join([f"{k}) {v}" for k, v in sorted(options.items())])
        
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, and astronomy. Analyze this scientific question carefully and determine the correct answer.

QUESTION:
{question}

OPTIONS:
{options_text}

Instructions:
1. Read the question carefully and identify what scientific concept or calculation is being tested
2. Work through the problem step-by-step, showing your reasoning
3. Consider all the given options and eliminate incorrect ones
4. Provide your final answer in the format: "Answer: X" where X is A, B, C, or D

Think systematically and use your scientific knowledge to solve this problem."""

        response = execute_llm(prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        if time.time() - start_time > timeout:
            return "A"
        
        # Extract answer using multiple strategies
        # Strategy 1: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer format: {answer}")
            return answer
        
        # Strategy 2: Look for final letter mentions
        # Find all isolated letters A, B, C, D in the response
        letters = re.findall(r'(?:^|\s)([A-D])(?:\s|$|\.)', response, re.MULTILINE)
        if letters:
            # Take the last mentioned letter as it's likely the final answer
            answer = letters[-1].upper()
            logging.info(f"Extracted last letter: {answer}")
            return answer
        
        # Strategy 3: Try a more direct follow-up prompt if first attempt unclear
        if time.time() - start_time < timeout - 10:
            direct_prompt = f"""Based on the following scientific question, select the single correct answer:

{question}

A) {options.get('A', '')}
B) {options.get('B', '')}
C) {options.get('C', '')}  
D) {options.get('D', '')}

Respond with only the letter of the correct answer (A, B, C, or D)."""
            
            direct_response = execute_llm(direct_prompt)
            
            # Look for single letter in direct response
            single_letter = re.search(r'\b([A-D])\b', direct_response)
            if single_letter:
                answer = single_letter.group(1).upper()
                logging.info(f"Direct prompt answer: {answer}")
                return answer
        
        # Fallback: Default to A
        logging.warning("Could not extract clear answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"