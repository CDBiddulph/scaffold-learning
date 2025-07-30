import logging
import re
import time
from llm_executor import execute_llm

def extract_question(input_string: str) -> str:
    """Extract the actual question from the input, removing metadata."""
    # Split by the metadata closing tag
    if '</question-metadata>' in input_string:
        parts = input_string.split('</question-metadata>', 1)
        if len(parts) > 1:
            return parts[1].strip()
    
    # Fallback: look for lines that don't contain XML tags
    lines = input_string.strip().split('\n')
    question_lines = []
    in_metadata = True
    
    for line in lines:
        if '</question-metadata>' in line:
            in_metadata = False
            continue
        if not in_metadata:
            question_lines.append(line)
    
    if question_lines:
        return '\n'.join(question_lines).strip()
    
    return input_string.strip()

def solve_scientific_question(question: str) -> str:
    """Use LLM to solve the scientific question with step-by-step reasoning."""
    prompt = f"""You are an expert scientist with deep knowledge across biology, chemistry, physics, and astronomy. Analyze this question carefully using step-by-step reasoning.

{question}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM analysis completed, response length: {len(response)}")
        return response
    except Exception as e:
        logging.error(f"Error getting LLM response: {e}")
        return ""

def extract_answer_letter(response: str) -> str:
    """Extract the final answer letter from the LLM response."""
    # Primary pattern: "Answer: X"
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Try other common patterns
    patterns = [
        r'The answer is\s*([A-D])',
        r'Therefore,?\s*the answer is\s*([A-D])',
        r'Final answer:\s*([A-D])',
        r'I choose\s*([A-D])',
        r'Option\s*([A-D])\s*is correct',
        r'([A-D])\s*is the correct answer',
        r'^([A-D])\)',  # Letter at start of line with parenthesis
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).upper()
    
    # Last resort: ask for clarification with a simpler prompt
    try:
        clarify_prompt = f"""Based on this analysis, what is the single letter answer?

{response}

Respond with just one letter (A, B, C, or D):"""
        
        clarification = execute_llm(clarify_prompt)
        # Look for any single letter A-D
        match = re.search(r'\b([A-D])\b', clarification.upper())
        if match:
            return match.group(1)
    except Exception as e:
        logging.error(f"Error in clarification: {e}")
    
    # Final fallback - look for any A-D in the original response
    letters = re.findall(r'\b([A-D])\b', response.upper())
    if letters:
        # Return the most common letter, or the last one mentioned
        return letters[-1]
    
    logging.warning("Could not extract answer, defaulting to A")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question content
        question = extract_question(input_string)
        logging.info(f"Extracted question: {question[:150]}...")
        
        # Check timeout buffer
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Get LLM analysis of the question
        analysis = solve_scientific_question(question)
        
        # Check timeout again
        if time.time() - start_time > 115:
            logging.warning("Timeout approaching after LLM analysis")
            return extract_answer_letter(analysis)
        
        # Extract the final answer letter
        answer = extract_answer_letter(analysis)
        logging.info(f"Final answer: {answer}")
        
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        # Return a reasonable default
        return "A"