import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Parse the input to extract the question content
    text = input_string.strip()
    
    # Find where the actual question starts (after the validation function)
    lines = text.split('\n')
    question_lines = []
    skip_validation = False
    
    for line in lines:
        # Skip the validation function block
        if 'def validate_answer' in line or '# Internal validation function' in line:
            skip_validation = True
            continue
        elif skip_validation and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            skip_validation = False
        
        # Add lines that aren't part of the validation function
        if not skip_validation and line.strip():
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    
    # Remove the standard instruction at the end if present
    standard_instruction = 'Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".'
    if question_text.endswith(standard_instruction):
        question_text = question_text[:-len(standard_instruction)].strip()
    
    # Check timeout
    if time.time() - start_time > 100:
        logging.warning("Approaching timeout, returning default")
        return "A"
    
    # Create a focused prompt for the LLM
    prompt = f"""You are an expert scientist with deep knowledge across all scientific fields including physics, chemistry, biology, astronomy, mathematics, and engineering.

Please solve this multiple choice question carefully:

{question_text}

Think through this step-by-step, showing your reasoning. Then provide your final answer in the exact format: "Answer: X" where X is A, B, C, or D."""

    try:
        response = execute_llm(prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Multiple strategies to extract the answer letter
        
        # Strategy 1: Look for "Answer: X" format (most reliable)
        answer_pattern = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_pattern:
            answer = answer_pattern.group(1).upper()
            logging.info(f"Extracted answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "Final answer: X" format
        final_pattern = re.search(r'Final\s+answer:\s*([ABCD])', response, re.IGNORECASE)
        if final_pattern:
            answer = final_pattern.group(1).upper()
            logging.info(f"Extracted answer using 'Final answer:' pattern: {answer}")
            return answer
        
        # Strategy 3: Look for option letters in parentheses, take the last one
        paren_options = re.findall(r'\(([ABCD])\)', response)
        if paren_options:
            answer = paren_options[-1].upper()
            logging.info(f"Extracted answer from parentheses: {answer}")
            return answer
        
        # Strategy 4: Look for any standalone letter A-D, take the last one
        standalone_letters = re.findall(r'\b([ABCD])\b', response)
        if standalone_letters:
            answer = standalone_letters[-1].upper()
            logging.info(f"Extracted answer as standalone letter: {answer}")
            return answer
        
        # Strategy 5: Last resort - look at the end of the response
        response_lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(response_lines[-3:]):  # Check last few lines
            if line.upper() in ['A', 'B', 'C', 'D']:
                answer = line.upper()
                logging.info(f"Extracted answer from end of response: {answer}")
                return answer
        
        logging.error(f"Failed to extract answer from response: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        return "A"  # Default fallback