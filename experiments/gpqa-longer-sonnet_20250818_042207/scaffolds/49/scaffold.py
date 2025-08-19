import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input - question followed by A) B) C) D) choices
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where answer choices start (first line beginning with "A)")
        answer_start_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^A\)\s', line):
                answer_start_idx = i
                break
        
        if answer_start_idx == -1:
            logging.error("Could not find answer choices starting with A)")
            return "A"
        
        # Split question from answers
        question_lines = lines[:answer_start_idx]
        answer_lines = lines[answer_start_idx:]
        
        # Remove the "Think step-by-step..." instruction from question if present
        question_text = '\n'.join(question_lines)
        think_instruction = r'Think step-by-step.*?Answer:\s*<letter>"?\.?\s*$'
        question_text = re.sub(think_instruction, '', question_text, flags=re.IGNORECASE | re.DOTALL).strip()
        
        answer_text = '\n'.join(answer_lines)
        
        logging.info(f"Question length: {len(question_text)}")
        logging.info(f"Found {len(answer_lines)} answer lines")
        
        # Check timeout buffer
        if time.time() - start_time > 90:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create expert-level prompt
        prompt = f"""You are a world-class expert scientist with deep knowledge in physics, chemistry, biology, astronomy, and mathematics. 

Solve this scientific question step by step:

{question_text}

Answer choices:
{answer_text}

Work through this systematically using your scientific expertise. Consider all relevant principles, formulas, and concepts. Show your reasoning clearly.

Provide your final answer in the format: "Answer: X" where X is A, B, C, or D."""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])\b',
            r'answer\s+is\s+([A-D])\b',
            r'correct\s+answer\s+is\s+([A-D])\b',
            r'Therefore,?\s*([A-D])\b',
            r'conclusion:\s*([A-D])\b'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # If no clear answer format, ask for clarification
        elapsed = time.time() - start_time
        if elapsed < 85:  # Leave time buffer
            clarify_prompt = f"""Based on your analysis, what is the single letter answer?

Your previous response:
{response[-400:]}

Respond with only the letter: A, B, C, or D"""
            
            clarify_response = execute_llm(clarify_prompt)
            logging.info(f"Clarification response: {clarify_response}")
            
            # Extract single letter
            letter_match = re.search(r'\b([A-D])\b', clarify_response)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Clarified answer: {answer}")
                return answer
        
        # Last resort - look for any mention of options in original response
        option_mentions = re.findall(r'\b(?:option\s+)?([A-D])\b', response, re.IGNORECASE)
        if option_mentions:
            answer = option_mentions[-1].upper()
            logging.info(f"Found option mention: {answer}")
            return answer
        
        logging.warning("Could not determine answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"