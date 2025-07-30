import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the actual question
        question_text = extract_question(input_string)
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Solve the question using the LLM
        answer = solve_scientific_question(question_text, start_time)
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_question(input_string: str) -> str:
    """Extract the actual question from the input, removing metadata"""
    lines = input_string.strip().split('\n')
    
    # Find where the actual question starts (after the metadata)
    question_start = 0
    for i, line in enumerate(lines):
        if '</question-metadata>' in line:
            question_start = i + 1
            break
    
    if question_start == 0:
        # If no metadata found, assume the whole input is the question
        question_start = 0
    
    # Extract the question text
    question_lines = lines[question_start:]
    question_text = '\n'.join(question_lines)
    
    # Remove the instruction at the end if present
    if 'Think step-by-step' in question_text:
        question_text = question_text.split('Think step-by-step')[0].strip()
    
    return question_text

def solve_scientific_question(question_text: str, start_time: float) -> str:
    """Use LLM to solve complex scientific questions with step-by-step reasoning"""
    
    # Check time remaining
    elapsed = time.time() - start_time
    if elapsed > 100:  # Leave 20 seconds buffer
        logging.warning("Approaching timeout, returning default")
        return "A"
    
    # Primary approach: detailed step-by-step analysis
    try:
        answer = solve_with_detailed_analysis(question_text, start_time)
        if answer:
            return answer
    except Exception as e:
        logging.error(f"Error in detailed analysis: {e}")
    
    # Fallback approach: direct answer
    try:
        answer = solve_direct(question_text, start_time)
        if answer:
            return answer
    except Exception as e:
        logging.error(f"Error in direct approach: {e}")
    
    return "A"  # Final fallback

def solve_with_detailed_analysis(question_text: str, start_time: float) -> str:
    """Solve question with detailed step-by-step analysis"""
    
    elapsed = time.time() - start_time
    if elapsed > 90:
        return None
    
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and related fields. 

Analyze this multiple choice question step by step:

{question_text}

Please follow this approach:
1. Identify the scientific discipline and key concepts involved
2. Break down what the question is asking
3. Apply relevant scientific principles, formulas, or theories
4. Work through any necessary calculations or logical reasoning
5. Evaluate each answer choice systematically
6. Select the most scientifically accurate answer

Think carefully and show your reasoning. End your response with "FINAL ANSWER: X" where X is the letter A, B, C, or D."""

    try:
        response = execute_llm(prompt)
        logging.info(f"Detailed analysis response: {response[-200:]}")
        return extract_answer_from_response(response)
    except Exception as e:
        logging.error(f"Error in detailed analysis LLM call: {e}")
        return None

def solve_direct(question_text: str, start_time: float) -> str:
    """Direct approach to get answer quickly"""
    
    elapsed = time.time() - start_time
    if elapsed > 105:
        return None
    
    prompt = f"""Answer this scientific multiple choice question. Choose the most correct answer.

{question_text}

Answer with just the letter: A, B, C, or D"""

    try:
        response = execute_llm(prompt)
        logging.info(f"Direct response: {response}")
        return extract_answer_from_response(response)
    except Exception as e:
        logging.error(f"Error in direct LLM call: {e}")
        return None

def extract_answer_from_response(response: str) -> str:
    """Extract the letter answer from LLM response"""
    
    # Look for "FINAL ANSWER: X" pattern
    final_match = re.search(r'FINAL ANSWER:\s*([ABCD])', response, re.IGNORECASE)
    if final_match:
        return final_match.group(1).upper()
    
    # Look for "Answer: X" pattern  
    answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for the letter at the end of the response
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        
        # Look for letter followed by )
        match = re.search(r'^([ABCD])\)', line)
        if match:
            return match.group(1)
    
    # Look for isolated letters in the response
    matches = re.findall(r'\b([ABCD])\b', response)
    if matches:
        # Return the last occurrence, as it's likely the final answer
        return matches[-1]
    
    logging.warning(f"Could not extract clear answer from response: {response}")
    return "A"  # Default fallback