import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        try:
            # Check timeout
            if time.time() - start_time > 100:
                logging.warning("Approaching timeout")
                return "A"
            
            # Clean input (remove ■ symbols that mark correct answers in training data)
            clean_input = re.sub(r'■\s*', '', input_string)
            lines = [line.strip() for line in clean_input.strip().split('\n') if line.strip()]
            
            # Find where options start
            option_start = -1
            for i, line in enumerate(lines):
                if re.match(r'^[ABCD]\)', line):
                    option_start = i
                    break
            
            if option_start == -1:
                logging.error("Could not find options in input")
                if attempt < max_retries:
                    continue
                return "A"
            
            # Extract question text
            question_text = '\n'.join(lines[:option_start]).strip()
            
            # Parse options (handle multi-line options)
            options = {}
            current_letter = None
            current_text = ""
            
            for line in lines[option_start:]:
                match = re.match(r'^([ABCD])\)\s*(.*)', line)
                if match:
                    # Save previous option if exists
                    if current_letter:
                        options[current_letter] = current_text.strip()
                    
                    current_letter = match.group(1)
                    current_text = match.group(2)
                else:
                    # Continuation of current option
                    if current_letter:
                        current_text += " " + line
            
            # Don't forget the last option
            if current_letter:
                options[current_letter] = current_text.strip()
            
            if len(options) < 4:
                logging.error(f"Only found {len(options)} options: {options}")
                if attempt < max_retries:
                    continue
                return "A"
            
            # Format options for the prompt
            options_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(options.items())])
            
            # Create comprehensive prompt
            system_prompt = "You are a world-class expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and other natural sciences."
            
            prompt = f"""Please analyze this scientific question step-by-step and select the correct answer.

Question:
{question_text}

Options:
{options_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""

            response = execute_llm(prompt, system_prompt)
            logging.info(f"LLM response (attempt {attempt + 1}): {response}")
            
            # Extract answer - look for "Answer: X" pattern first
            answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
            if answer_match:
                final_answer = answer_match.group(1).upper()
                logging.info(f"Extracted answer: {final_answer}")
                return final_answer
            
            # Fallback: look for the last occurrence of A, B, C, or D
            letters = re.findall(r'\b([ABCD])\b', response)
            if letters:
                final_answer = letters[-1].upper()
                logging.info(f"Extracted fallback answer: {final_answer}")
                return final_answer
            
            logging.warning(f"Could not extract answer from attempt {attempt + 1}: {response[:200]}...")
            
        except Exception as e:
            logging.error(f"Error on attempt {attempt + 1}: {e}")
            
        if attempt < max_retries:
            logging.info(f"Retrying... (attempt {attempt + 2})")
    
    logging.error("All attempts failed, returning default answer")
    return "A"