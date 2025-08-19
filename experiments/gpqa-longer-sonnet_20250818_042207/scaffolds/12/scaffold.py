import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_limit = 110  # Conservative timeout to avoid hitting 120s limit
    
    try:
        logging.info("Starting to process scientific multiple choice question")
        
        # Split input into lines for parsing
        lines = input_string.strip().split('\n')
        
        # Locate the start of multiple choice options (line beginning with "A)")
        option_start_line = -1
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if re.match(r'^A\)', stripped_line):
                option_start_line = i
                break
        
        if option_start_line == -1:
            logging.error("Could not locate option A) in the input text")
            return "A"  # Default fallback
        
        # Find where options end (look for "Think step-by-step" instruction)
        option_end_line = len(lines)
        for i in range(option_start_line, len(lines)):
            if "Think step-by-step" in lines[i]:
                option_end_line = i
                break
        
        # Extract the question text (everything before the options)
        question_text = '\n'.join(lines[:option_start_line]).strip()
        
        # Extract the options text (from option start to end)
        options_text = '\n'.join(lines[option_start_line:option_end_line]).strip()
        
        logging.info(f"Parsed question (first 100 chars): {question_text[:100]}...")
        logging.info(f"Parsed options with {len([l for l in lines[option_start_line:option_end_line] if l.strip().startswith(('A)', 'B)', 'C)', 'D)'))])} choices")
        
        # Check if we're running close to timeout
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_limit:
            logging.warning(f"Timeout approaching ({elapsed_time:.1f}s), using fallback")
            return "A"
        
        # Construct the prompt for the LLM
        llm_prompt = f"""Please solve this scientific multiple choice question step by step.

QUESTION:
{question_text}

ANSWER CHOICES:
{options_text}

Work through the problem systematically, applying relevant scientific principles, equations, and calculations as needed. Consider each option carefully. Then provide your final answer in the exact format: "Answer: X" where X is the letter A, B, C, or D."""

        # Send query to LLM
        logging.info("Submitting question to LLM...")
        llm_response = execute_llm(llm_prompt)
        logging.info(f"Received LLM response ({len(llm_response)} characters)")
        
        # Parse the answer from LLM response
        # First try to find explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', llm_response, re.IGNORECASE)
        if answer_match:
            extracted_answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {extracted_answer}")
            return extracted_answer
        
        # Fallback: look for the last occurrence of a standalone letter A, B, C, or D
        standalone_letters = re.findall(r'\b([A-D])\b', llm_response)
        if standalone_letters:
            extracted_answer = standalone_letters[-1].upper()
            logging.info(f"Using fallback extraction method, answer: {extracted_answer}")
            return extracted_answer
        
        # If all else fails, log the issue and return default
        logging.error("Failed to extract answer from LLM response")
        logging.error(f"LLM response preview: {llm_response[:300]}...")
        return "A"
        
    except Exception as exception:
        logging.error(f"Exception during processing: {str(exception)}")
        return "A"