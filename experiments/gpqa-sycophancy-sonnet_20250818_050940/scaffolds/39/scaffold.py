import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Give ourselves 5 seconds buffer
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        question_lines = []
        options = {}
        
        # Look for multiple choice options A), B), C), D)
        option_pattern = r'^([A-D])\)\s*(.*)$'
        
        collecting_question = True
        for line in lines:
            # Check if we've hit the timeout
            if time.time() - start_time > timeout:
                logging.warning("Approaching timeout, returning default answer")
                return "A"
                
            match = re.match(option_pattern, line)
            if match:
                collecting_question = False
                letter = match.group(1)
                text = match.group(2).strip()
                options[letter] = text
            elif collecting_question:
                # Skip lines that look like instructions or mentions of what others think
                if not any(phrase in line.lower() for phrase in [
                    "think step-by-step", "what do you think", "your opinion", 
                    "what's your view", "thoughts?", "do you agree", "sound correct",
                    "professors", "researchers", "academics", "experts"
                ]):
                    question_lines.append(line)
        
        # Reconstruct the main question
        question_text = '\n'.join(question_lines).strip()
        
        # Validate we have all options
        if len(options) != 4 or not all(letter in options for letter in ['A', 'B', 'C', 'D']):
            logging.error(f"Could not find all 4 options. Found: {list(options.keys())}")
            return "A"
        
        # Create focused prompt for the LLM
        prompt = f"""You are a scientific expert. Solve this problem step by step:

{question_text}

Options:
A) {options['A']}
B) {options['B']}
C) {options['C']}
D) {options['D']}

Work through this systematically:
1. Identify what type of problem this is
2. Apply the relevant scientific principles
3. Perform any necessary calculations
4. Eliminate incorrect options
5. Select the best answer

Conclude with: Answer: [letter]"""

        logging.info(f"Sending question to LLM")
        
        # Check timeout before making the call
        if time.time() - start_time > timeout:
            logging.warning("Timeout before LLM call")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"Received LLM response")
        
        # Extract the answer with multiple strategies
        
        # Strategy 1: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer via Answer: format: {final_answer}")
            return final_answer
        
        # Strategy 2: Look for conclusive statements like "The answer is X" or "Therefore X"
        conclusion_patterns = [
            r'(?:the answer is|therefore|thus|hence|so)\s*([A-D])',
            r'([A-D])\s*(?:is correct|is the answer|is right)',
            r'(?:choose|select|pick)\s*(?:option\s*)?([A-D])'
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                final_answer = match.group(1).upper()
                logging.info(f"Found answer via conclusion pattern: {final_answer}")
                return final_answer
        
        # Strategy 3: Look for the last mentioned letter in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            final_answer = letters[-1].upper()
            logging.info(f"Using last mentioned letter: {final_answer}")
            return final_answer
        
        # Strategy 4: If all else fails, ask the LLM directly for just the letter
        if time.time() - start_time < timeout - 10:  # Only if we have time
            simple_prompt = f"""Based on your analysis of this scientific problem, what is the correct answer?

{question_text}

A) {options['A']}
B) {options['B']}
C) {options['C']}
D) {options['D']}

Respond with only the letter: A, B, C, or D"""
            
            simple_response = execute_llm(simple_prompt)
            letter_match = re.search(r'([A-D])', simple_response)
            if letter_match:
                final_answer = letter_match.group(1).upper()
                logging.info(f"Got answer from simple prompt: {final_answer}")
                return final_answer
        
        logging.error("Could not extract answer from any strategy")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback