import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check if we're running out of time (keep 15 second buffer)
        if time.time() - start_time > 105:  
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Construct a prompt for the LLM
        prompt = f"""You are answering a multiple choice question from a high-level scientific competition. These questions test expert knowledge across physics, chemistry, biology, astronomy, and mathematics.

{input_string.strip()}

Approach this systematically:
1. Identify what scientific principles/concepts are being tested
2. Recall relevant formulas, mechanisms, or theoretical frameworks  
3. Work through any calculations or logical steps carefully
4. Consider each option and eliminate any that are clearly incorrect
5. Select the best answer based on your analysis

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"
"""

        # Get the LLM's response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # Extract the final answer from the response
        # Look for "Answer: X" pattern first (most reliable)
        answer_pattern = re.compile(r'Answer:\s*([A-D])', re.IGNORECASE)
        match = answer_pattern.search(response)
        
        if match:
            answer = match.group(1).upper()
            logging.info(f"Extracted answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Fallback patterns in order of preference
        fallback_patterns = [
            (r'The correct answer is\s*([A-D])', 'correct answer is'),
            (r'The answer is\s*([A-D])', 'answer is'),
            (r'Therefore,?\s*([A-D])', 'therefore'),
            (r'Thus,?\s*([A-D])', 'thus'),
            (r'So,?\s*([A-D])', 'so'),
            (r'Option\s*([A-D])\s*is\s*correct', 'option X is correct'),
            (r'\b([A-D])\s*is\s*the\s*correct', 'X is the correct'),
            (r'choose\s*([A-D])', 'choose'),
            (r'select\s*([A-D])', 'select'),
        ]
        
        for pattern, description in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer via '{description}' pattern: {answer}")
                return answer
        
        # Final fallback: Look for standalone letters in the last part of response
        lines = response.split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            # Look for a line that contains just a letter (possibly with some whitespace/punctuation)
            clean_line = re.sub(r'[^\w]', '', line.upper())
            if clean_line in ['A', 'B', 'C', 'D']:
                logging.info(f"Extracted answer from clean line: {clean_line}")
                return clean_line
            
            # Look for any letter in the line
            single_letter_match = re.search(r'\b([A-D])\b', line.upper())
            if single_letter_match:
                answer = single_letter_match.group(1)
                logging.info(f"Extracted answer from single letter: {answer}")
                return answer
        
        logging.error("Could not extract answer from LLM response - no recognizable patterns found")
        logging.error(f"Response was: {response[-200:]}")  # Log last 200 chars for debugging
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback