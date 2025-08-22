import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """Process a scientific multiple choice question and return the answer letter."""
    
    start_time = time.time()
    timeout = 115  # Leave 5 seconds buffer before the 120s timeout
    
    try:
        # Parse the input to extract question and options
        text = input_string.strip()
        
        # Split the text into lines
        lines = text.split('\n')
        
        # Find where options start (lines beginning with A), B), C), D) or A, B, C, D)
        question_lines = []
        options = {}
        in_options = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for option patterns: A) text or A text
            option_match = re.match(r'^([ABCD])\)?\s*(.*)', line)
            if option_match and not in_options:
                # This might be the start of options, check if it looks like an option
                letter = option_match.group(1)
                text_part = option_match.group(2).strip()
                # If it starts with A and has substantial text, likely an option
                if letter == 'A' and text_part:
                    in_options = True
                    options[letter] = text_part
                elif not in_options:
                    question_lines.append(line)
            elif option_match and in_options:
                letter = option_match.group(1)
                text_part = option_match.group(2).strip()
                options[letter] = text_part
            elif not in_options:
                question_lines.append(line)
        
        # Clean up question text by removing the "Think step-by-step" instruction
        question_text = ' '.join(question_lines)
        question_text = re.sub(r'Think step-by-step.*?Answer:\s*[<&]letter[>&].*$', '', question_text, flags=re.IGNORECASE | re.DOTALL).strip()
        
        logging.info(f"Parsed question: {question_text[:200]}...")
        logging.info(f"Options found: {list(options.keys())}")
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return 'A'
        
        # Construct prompt for the LLM
        prompt = f"""Please solve this scientific problem step by step and provide the correct answer.

Question: {question_text}

Answer choices:
"""
        
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                prompt += f"{letter}) {options[letter]}\n"
        
        prompt += """
Please analyze this problem carefully:
1. Identify the key scientific concepts involved
2. Work through any necessary calculations or reasoning
3. Consider each answer choice
4. Provide your final answer as just the letter (A, B, C, or D) at the end

Your response should end with just the answer letter on its own line."""

        # Call LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Check timeout after LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached after LLM call")
            return 'A'
        
        # Extract the answer from the response
        response_lines = response.strip().split('\n')
        
        # Look for the last line that is just a single letter
        for line in reversed(response_lines):
            line = line.strip()
            if re.match(r'^[ABCD]$', line):
                logging.info(f"Found answer: {line}")
                return line
        
        # Look for answer in context like "Answer: X" or "The answer is X"
        for line in reversed(response_lines[-10:]):  # Check last 10 lines
            matches = re.findall(r'\b([ABCD])\b', line)
            if matches:
                answer = matches[-1]  # Take the last match in the line
                logging.info(f"Extracted answer '{answer}' from line: {line}")
                return answer
        
        # If no clear answer found, default to A
        logging.warning("Could not parse answer from LLM response, defaulting to A")
        logging.warning(f"Last few lines of response: {response_lines[-5:]}")
        return 'A'
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        logging.error(f"Input was: {input_string[:500]}...")
        return 'A'  # Safe fallback