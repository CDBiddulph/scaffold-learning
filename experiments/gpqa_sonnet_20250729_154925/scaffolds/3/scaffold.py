import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        # Extract the actual question content, skipping the metadata
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after the metadata)
        question_start = 0
        for i, line in enumerate(lines):
            if '</question-metadata>' in line:
                question_start = i + 1
                break
        
        if question_start == 0:
            # No metadata found, assume entire input is the question
            question_text = input_string
        else:
            question_text = '\n'.join(lines[question_start:])
        
        logging.info(f"Processing question of length: {len(question_text)}")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Ask the LLM to solve the question with clear instructions
        prompt = f"""You are an expert scientist with deep knowledge across multiple disciplines including chemistry, biology, physics, astronomy, and mathematics.

Please solve this multiple choice question step by step:
1. Read the question carefully
2. Analyze each option systematically 
3. Use your scientific knowledge to determine the correct answer
4. End your response with exactly "Answer: X" where X is A, B, C, or D

{question_text}"""

        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found clear answer pattern: {answer}")
            return answer
        
        # Look for other common answer patterns in order of reliability
        patterns = [
            r'(?:the\s+(?:correct\s+)?answer\s+is|therefore\s+the\s+answer\s+is)\s*([ABCD])',
            r'(?:thus|hence|so)\s*(?:the\s+answer\s+is\s*)?([ABCD])',
            r'(?:choose|select|pick)\s*(?:option\s*)?([ABCD])',
            r'\b([ABCD])\s*(?:is\s+(?:the\s+)?correct|is\s+(?:the\s+)?answer)',
            r'(?:option|choice)\s*([ABCD])\s*(?:is\s+correct|is\s+right)',
            r'final\s+answer.*?([ABCD])',
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer via pattern {i}: {answer}")
                return answer
        
        # If no clear pattern, look for the most likely letter in context
        # Split into sentences and look for letters mentioned near conclusion words
        sentences = re.split(r'[.!?]', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            if any(word in sentence.lower() for word in ['therefore', 'thus', 'so', 'answer', 'correct']):
                letters = re.findall(r'\b([ABCD])\b', sentence)
                if letters:
                    answer = letters[-1].upper()
                    logging.info(f"Using contextual letter: {answer}")
                    return answer
        
        # Look for the last standalone letter in the entire response
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("No answer pattern found, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"