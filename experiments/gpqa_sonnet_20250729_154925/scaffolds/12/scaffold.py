import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer before the 120s limit
    
    try:
        # Parse the input to extract the question
        question_text = extract_question(input_string)
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use LLM to answer the question
        answer = answer_question(question_text)
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_question(input_string: str) -> str:
    """Extract the actual question from the input, ignoring metadata"""
    
    # Find the end of the metadata block
    metadata_end = input_string.find('</question-metadata>')
    if metadata_end != -1:
        # Extract everything after the metadata
        question_text = input_string[metadata_end + len('</question-metadata>'):].strip()
    else:
        # If no metadata found, use the whole input
        question_text = input_string.strip()
    
    return question_text

def answer_question(question_text: str) -> str:
    """Use LLM to answer the multiple choice question"""
    
    prompt = f"""You are a scientific expert answering a multiple choice question. Analyze the question carefully using your knowledge of science.

{question_text}

Please think through this step-by-step and provide your reasoning, then give your final answer as just the letter A, B, C, or D at the end.

End your response with "FINAL: X" where X is your chosen letter."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer
        answer = extract_final_answer(response)
        return answer
        
    except Exception as e:
        logging.error(f"Error getting LLM response: {e}")
        return "A"

def extract_final_answer(response: str) -> str:
    """Extract the final answer letter from the LLM response"""
    
    # Look for "FINAL: X" pattern
    match = re.search(r'FINAL:\s*([ABCD])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for "Answer: X" pattern (as requested in some questions)
    match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for "Final Answer: X" pattern
    match = re.search(r'Final Answer:\s*([ABCD])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for just a letter at the end of a line
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Check if line ends with one of the letters
        match = re.search(r'\b([ABCD])\s*$', line)
        if match:
            return match.group(1).upper()
    
    # Look for any pattern like "The answer is X" or similar
    match = re.search(r'(?:answer is|choose|select)\s*([ABCD])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Last resort: find any single letter in the response (prefer later ones)
    matches = re.findall(r'\b([ABCD])\b', response)
    if matches:
        return matches[-1].upper()
    
    logging.warning(f"Could not extract answer from LLM response: {response[:200]}...")
    return "A"