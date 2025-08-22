import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing scientific multiple choice question")
    
    lines = input_string.strip().split('\n')
    choices = {}
    question_lines = []
    
    # Parse input to separate question from answer choices
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match answer choice patterns: A), A ~, A text, etc.
        match = re.match(r'^([A-D])[\)\s~]*\s*(.+)$', line)
        if match and len(line.split()) > 1:  # Ensure it's not just a single letter
            letter = match.group(1)
            text = match.group(2).strip()
            choices[letter] = text
            logging.info(f"Found choice {letter}: {text[:50]}...")
        else:
            question_lines.append(line)
    
    # Reconstruct question text
    question = '\n'.join(question_lines).strip()
    
    # Remove common instruction text that appears at the end
    question = re.sub(r'Think step-by-step.*$', '', question, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE).strip()
    
    if not choices:
        logging.error("No answer choices found in input")
        return "A"
    
    logging.info(f"Question length: {len(question)}, Found {len(choices)} choices")
    
    # Format choices for the prompt
    choices_text = []
    for letter in ['A', 'B', 'C', 'D']:
        if letter in choices:
            choices_text.append(f"{letter}) {choices[letter]}")
    
    # Create comprehensive prompt leveraging LLM's scientific expertise
    prompt = f"""You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, and other sciences. Please solve this multiple choice question by analyzing it step by step.

{question}

{chr(10).join(choices_text)}

Please think through this problem carefully, show your reasoning, and conclude with your final answer in the exact format "Answer: X" where X is the correct letter (A, B, C, or D)."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Primary strategy: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer: {result}")
            return result
        
        # Fallback: Find the last occurrence of any choice letter
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            result = letters[-1].upper()
            logging.info(f"Using fallback answer: {result}")
            return result
            
        logging.error("Could not extract answer from LLM response")
        return "A"  # Safe fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"