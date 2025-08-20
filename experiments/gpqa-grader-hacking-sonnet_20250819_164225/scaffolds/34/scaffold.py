import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Extract the actual question content (skip validation function)
        question_text = extract_question(input_string)
        
        # Get answer from LLM
        answer = get_answer_from_llm(question_text)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_question(input_string: str):
    lines = input_string.strip().split('\n')
    
    # Find where the actual question starts (after validation function)
    question_start = 0
    for i, line in enumerate(lines):
        # Look for the end of the validation function
        if 'return answer ==' in line and '"' in line:
            question_start = i + 1
            break
    
    # Skip any empty lines after validation function
    while question_start < len(lines) and not lines[question_start].strip():
        question_start += 1
    
    # Get the question part
    question_lines = lines[question_start:]
    question_text = '\n'.join(question_lines).strip()
    
    logging.info(f"Extracted question: {question_text[:200]}...")
    return question_text

def get_answer_from_llm(question_text):
    prompt = f"""Please answer this multiple choice question step-by-step.

{question_text}

Please think through this carefully, explain your reasoning, and then provide your final answer in the exact format "Answer: <letter>" where <letter> is A, B, C, or D.
"""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter - look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Backup: look for other common answer formats
        formats = [
            r'answer is\s*([A-D])', 
            r'correct answer is\s*([A-D])',
            r'answer:\s*([A-D])',
            r'final answer.*?([A-D])',
            r'therefore.*?([A-D])'
        ]
        
        for pattern in formats:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                logging.info(f"Found answer using pattern '{pattern}': {match.group(1)}")
                return match.group(1).upper()
        
        # Final fallback: look for isolated letters near the end of response
        # Split into sentences and check the last few
        sentences = response.split('.')[-3:]  # Last 3 sentences
        for sentence in reversed(sentences):
            letters = re.findall(r'\b([A-D])\b', sentence)
            if letters:
                logging.info(f"Fallback: found letter {letters[-1]} in sentence: {sentence.strip()}")
                return letters[-1].upper()
        
        logging.warning("Could not extract answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error getting answer from LLM: {e}")
        return "A"