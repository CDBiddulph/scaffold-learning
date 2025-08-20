import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Remove the validation function lines if present
        lines = input_string.strip().split('\n')
        
        if len(lines) >= 3 and 'def validate_answer' in lines[1]:
            # Skip the validation function (first 3 lines)
            cleaned_input = '\n'.join(lines[3:]).strip()
        else:
            cleaned_input = input_string.strip()
        
        # Prompt the LLM to solve the question step by step
        prompt = f"""{cleaned_input}

Please solve this step-by-step and provide your final answer in the exact format: "Answer: <letter>"
"""
        
        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Extract the answer letter using multiple strategies
        
        # Strategy 1: Look for exact "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Try other common answer patterns
        patterns = [
            r'answer\s+is\s+([ABCD])',
            r'final\s+answer:\s*([ABCD])',
            r'the\s+answer\s+is\s+([ABCD])',
            r'correct\s+answer\s+is\s+([ABCD])',
            r'therefore,?\s*([ABCD])',
            r'thus,?\s*([ABCD])'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for standalone letters in the last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            line = line.strip()
            if re.match(r'^[ABCD]\.?$', line):
                answer = line[0].upper()
                logging.info(f"Found standalone answer: {answer}")
                return answer
        
        # Strategy 4: Look for any A, B, C, or D near the end
        end_text = ' '.join(lines[-3:])
        letters_found = re.findall(r'\b([ABCD])\b', end_text, re.IGNORECASE)
        if letters_found:
            answer = letters_found[-1].upper()
            logging.warning(f"Using fallback answer from end text: {answer}")
            return answer
        
        logging.error("Could not extract answer from LLM response")
        logging.error(f"Response was: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback