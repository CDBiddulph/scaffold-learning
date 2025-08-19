import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # The input already contains good instructions, just add clarity for the final answer format
        prompt = input_string.strip() + "\n\nPlease end your response with 'Answer: <letter>' where <letter> is A, B, C, or D."

        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Check timeout - leave buffer time
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout")
            
        # Extract answer using multiple strategies
        response_upper = response.upper()
        
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'ANSWER:\s*([A-D])', response_upper)
        if answer_match:
            answer = answer_match.group(1)
            logging.info(f"Found answer '{answer}' using Answer: pattern")
            return answer
            
        # Strategy 2: Look at the last few lines for a single letter
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        for line in reversed(lines[-3:]):  # Check last 3 lines
            line_upper = line.upper().strip()
            if line_upper in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer '{line_upper}' as standalone letter")
                return line_upper
                
        # Strategy 3: Look for other common answer patterns
        patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'THE ANSWER IS\s*([A-D])',
            r'CORRECT ANSWER:\s*([A-D])',
            r'MY ANSWER:\s*([A-D])',
            r'ANSWER\s+([A-D])',
            r'\b([A-D])\s*(?:is|are)?\s*(?:the)?\s*(?:correct|right|answer)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response_upper)
            if matches:
                answer = matches[-1]  # Take the last match
                logging.info(f"Found answer '{answer}' using pattern: {pattern}")
                return answer
                
        # Strategy 4: Look for letters at the end of lines
        for line in reversed(lines):
            line_clean = re.sub(r'[^A-D]', '', line.upper())
            if len(line_clean) == 1 and line_clean in 'ABCD':
                logging.info(f"Found answer '{line_clean}' at end of line")
                return line_clean
                
        # Strategy 5: Find the last occurrence of A, B, C, or D in the response
        # Remove common words to avoid false positives
        filtered_response = response_upper
        for word in ['ANSWER', 'QUESTION', 'OPTION', 'CHOICE', 'PART', 'SECTION']:
            filtered_response = filtered_response.replace(word, '')
            
        for char in reversed(filtered_response):
            if char in 'ABCD':
                logging.info(f"Found answer '{char}' using fallback method")
                return char
                
        # Ultimate fallback - should rarely happen
        logging.warning("Could not extract answer from response, defaulting to A")
        logging.warning(f"Response was: {response[:200]}...")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Even if something goes wrong, return a valid answer
        return 'A'