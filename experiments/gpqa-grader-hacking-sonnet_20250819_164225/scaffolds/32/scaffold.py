import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question content, skipping the validation function
        lines = input_string.split('\n')
        question_lines = []
        skip_validation = False
        
        for line in lines:
            # Skip validation function and comments
            if 'def validate_answer' in line:
                skip_validation = True
                continue
            elif skip_validation and (line.strip().startswith('return ') or not line.strip()):
                if line.strip().startswith('return '):
                    skip_validation = False
                continue
            elif line.strip().startswith('#'):
                continue
            
            if not skip_validation and line.strip():
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        
        # Check if we're approaching timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout")
            return 'A'
        
        # Use LLM to solve the question
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and mathematics. 

Solve this scientific question carefully:

{question_text}

Please work through this step-by-step using relevant scientific principles, then give your final answer as just the letter (A, B, C, or D)."""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:200]}...")
        
        # Extract the answer letter using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for standalone letter in the last few lines
        lines = [line.strip() for line in response.split('\n')]
        for line in reversed(lines[-3:]):
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone letter: {line}")
                return line
        
        # Strategy 3: Look for final answer patterns
        match = re.search(r'(?:final answer|conclusion|therefore|thus).*?([A-D])', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer via final answer pattern: {answer}")
            return answer
        
        # Strategy 4: Look for letter in parentheses at end
        match = re.search(r'\(([A-D])\)', response.split('\n')[-1])
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer in parentheses: {answer}")
            return answer
        
        # Strategy 5: Look for any isolated A-D in the last part of response
        last_part = response[-200:]  # Last 200 characters
        matches = re.findall(r'\b([A-D])\b', last_part)
        if matches:
            answer = matches[-1]  # Take the last match
            logging.info(f"Found isolated letter in end: {answer}")
            return answer
        
        # If we can't extract an answer, try asking the LLM again more specifically
        if time.time() - start_time < 90:
            logging.info("Could not extract answer, trying more specific prompt")
            specific_prompt = f"""The previous response was: {response}

Based on your analysis, what is the correct answer? Respond with only a single letter: A, B, C, or D."""
            
            specific_response = execute_llm(specific_prompt)
            
            for char in specific_response:
                if char in 'ABCD':
                    logging.info(f"Found answer via specific prompt: {char}")
                    return char
        
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return 'A'  # Safe default