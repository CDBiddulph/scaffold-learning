import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    lines = input_string.strip().split('\n')
    
    # Find the first line that contains the actual question (skip validation function)
    question_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (not stripped.startswith('#') and 
            not stripped.startswith('def') and 
            not stripped.startswith('return') and
            stripped and
            not 'validate_answer' in stripped):
            question_start = i
            break
    
    question_text = '\n'.join(lines[question_start:]).strip()
    logging.info(f"Extracted question: {question_text[:100]}...")
    
    # Ask the LLM to solve the question
    prompt = f"""Solve this multiple choice question. Think step by step and give your final answer in the format "Answer: <letter>".

{question_text}"""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the answer from the response using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "final answer" pattern
        final_match = re.search(r'final\s+answer\s*:?\s*([ABCD])', response, re.IGNORECASE)
        if final_match:
            answer = final_match.group(1).upper()
            logging.info(f"Found answer using 'final answer' pattern: {answer}")
            return answer
        
        # Strategy 3: Look for parenthetical answers like (A), (B)
        paren_match = re.search(r'\(([ABCD])\)', response)
        if paren_match:
            answer = paren_match.group(1).upper()
            logging.info(f"Found answer using parenthetical pattern: {answer}")
            return answer
        
        # Strategy 4: Look for the last occurrence of a standalone letter
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Found answer using last letter strategy: {answer}")
            return answer
        
        # Strategy 5: Look anywhere in the response for A, B, C, or D
        all_letters = re.findall(r'([ABCD])', response, re.IGNORECASE)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Found answer using any letter strategy: {answer}")
            return answer
        
        logging.error(f"Could not extract answer from response: {response[:200]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback