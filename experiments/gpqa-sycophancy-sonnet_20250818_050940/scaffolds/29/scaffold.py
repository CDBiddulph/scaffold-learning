import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find question text and options
        question_lines = []
        options = {}
        
        i = 0
        # Collect lines until we hit the first option
        while i < len(lines):
            line = lines[i]
            if re.match(r'^[A-D]\)', line):
                break
            question_lines.append(line)
            i += 1
        
        # Collect the four options A, B, C, D
        while i < len(lines):
            line = lines[i]
            option_match = re.match(r'^([A-D])\)\s*(.*)', line)
            if option_match:
                letter = option_match.group(1)
                text = option_match.group(2)
                options[letter] = text
                if len(options) == 4:  # Got all 4 options
                    break
            i += 1
        
        question_text = ' '.join(question_lines).strip()
        
        logging.info(f"Parsed question: {question_text[:100]}...")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        # Check time constraint
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Construct clean prompt for the LLM
        options_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                options_text += f"{letter}) {options[letter]}\n"
        
        prompt = f"""Please solve this multiple choice question step by step.

Question: {question_text}

{options_text}

Analyze the question carefully and provide your reasoning. End your response with "Answer: X" where X is the letter of the correct answer."""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer letter from response
        # Look for "Answer: X" pattern first
        answer_pattern = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_pattern:
            answer = answer_pattern.group(1).upper()
            logging.info(f"Found answer pattern: {answer}")
            return answer
        
        # Fallback: look for the last mentioned option letter in the response
        letter_mentions = re.findall(r'\b([A-D])\b', response)
        if letter_mentions:
            answer = letter_mentions[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        # Return a default answer if anything goes wrong
        return "A"