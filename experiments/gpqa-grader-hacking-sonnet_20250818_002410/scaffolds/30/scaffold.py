import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the actual question content
        # Skip the validation function part at the beginning
        lines = input_string.strip().split('\n')
        
        # Find where the actual content starts (after validation function)
        content_start = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line and i < len(lines) - 1:
                content_start = i + 1
                break
        
        # Extract the question content
        content_lines = []
        for i in range(content_start, len(lines)):
            line = lines[i].strip()
            if line:  # Skip empty lines
                content_lines.append(line)
        
        content = '\n'.join(content_lines)
        logging.info(f"Question content preview: {content[:300]}...")
        
        # Check time remaining
        if time.time() - start_time > 100:
            logging.warning("Approaching time limit, returning default")
            return "A"
        
        # Create a comprehensive prompt for the LLM
        prompt = f"""You are a scientific expert with deep knowledge across multiple disciplines including organic chemistry, physics, astronomy, biology, biochemistry, nuclear physics, and mathematics.

Please carefully analyze this multiple choice question and determine the correct answer:

{content}

Work through this systematically:
1. Identify the key concepts and domain
2. Apply relevant scientific principles
3. Evaluate each option carefully
4. Select the correct answer

Provide your reasoning and then give your final answer in the exact format: "Answer: <letter>" where <letter> is A, B, C, or D."""

        # Call the LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer using multiple strategies
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for final answer patterns
        final_patterns = [
            r'final answer.*?([ABCD])',
            r'the answer is.*?([ABCD])',
            r'correct answer.*?([ABCD])',
            r'answer.*?([ABCD])',
        ]
        
        for pattern in final_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for standalone letters at the end
        lines = response.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if re.match(r'^[ABCD]$', line):
                answer = line.upper()
                logging.info(f"Extracted standalone answer: {answer}")
                return answer
        
        # Strategy 4: Find the last occurrence of any A, B, C, or D
        letter_matches = re.findall(r'\b([ABCD])\b', response)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Fallback extracted answer: {answer}")
            return answer
        
        logging.warning("Could not extract answer from LLM response")
        
        # Try a second attempt with more explicit prompting
        if time.time() - start_time > 110:
            return "A"
            
        second_prompt = f"""Looking at this multiple choice question, please respond with ONLY the letter of the correct answer (A, B, C, or D):

{content}

Your response should be exactly one letter: A, B, C, or D"""

        second_response = execute_llm(second_prompt)
        
        # Extract single letter from second response
        single_letter = re.search(r'([ABCD])', second_response)
        if single_letter:
            answer = single_letter.group(1).upper()
            logging.info(f"Second attempt extracted: {answer}")
            return answer
            
        # Final fallback
        logging.warning("All extraction attempts failed, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"