import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove the validation function part and extract the actual question
        lines = input_string.strip().split('\n')
        
        content_lines = []
        in_validation_function = False
        
        for line in lines:
            # Skip the validation function block
            if line.startswith('#') and 'validation function' in line:
                in_validation_function = True
                continue
            elif in_validation_function:
                if line.startswith('def') or line.strip().startswith('return') or line.strip() == '':
                    if line.strip().startswith('return'):
                        in_validation_function = False
                    continue
                else:
                    in_validation_function = False
            
            if not in_validation_function:
                content_lines.append(line)
        
        # Join the content back together
        question_content = '\n'.join(content_lines).strip()
        
        logging.info("Extracted question content for LLM processing")
        
        # Create a clear prompt for the LLM
        prompt = f"""{question_content}

Please solve this academic problem step-by-step, showing your reasoning clearly. Then provide your final answer in exactly this format: "Answer: X" where X is the letter A, B, C, or D."""
        
        # Check if we're approaching timeout
        if time.time() - start_time > 100:  # Leave 20 second buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Get response from LLM
        response = execute_llm(prompt)
        
        logging.info("Received response from LLM")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer: X' pattern: {final_answer}")
            return final_answer
        
        # Strategy 2: Look for isolated letters at the end of response
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found isolated letter answer: {line}")
                return line
        
        # Strategy 3: Look for common answer patterns
        last_part = ' '.join(response_lines[-3:]).strip()  # Last 3 lines
        patterns = [
            r'(?:the\s+)?(?:correct\s+)?(?:answer\s+is\s*|choice\s+is\s*|option\s+is\s*)([ABCD])',
            r'(?:answer|choice|option):\s*([ABCD])',
            r'therefore[,\s]*([ABCD])',
            r'thus[,\s]*([ABCD])',
            r'so[,\s]*([ABCD])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, last_part, re.IGNORECASE)
            if match:
                final_answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {final_answer}")
                return final_answer
        
        # Strategy 4: Look for any single letter near the end
        # Find all isolated letters in the last part of the response
        letter_matches = re.findall(r'\b([ABCD])\b', last_part)
        if letter_matches:
            final_answer = letter_matches[-1].upper()  # Take the last one
            logging.info(f"Found answer from isolated letters: {final_answer}")
            return final_answer
        
        # Strategy 5: Scan entire response for letters (last resort)
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            final_answer = all_letters[-1].upper()  # Take the last occurrence
            logging.info(f"Using last letter found in entire response: {final_answer}")
            return final_answer
        
        # Default fallback
        logging.warning("Could not extract any clear answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default fallback