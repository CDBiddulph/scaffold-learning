import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s timeout
    
    try:
        # Parse input to extract question content
        question_content = extract_question_content(input_string)
        logging.info(f"Extracted question content: {question_content[:200]}...")
        
        # Check timeout before proceeding
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before processing")
            return "A"
        
        # Solve the question using LLM
        answer = solve_question(question_content, start_time, timeout)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback

def extract_question_content(input_string: str) -> str:
    """Extract the actual question content from input, removing metadata"""
    lines = input_string.strip().split('\n')
    
    # Find where metadata ends - look for closing tag
    question_start = 0
    for i, line in enumerate(lines):
        if '</question-metadata>' in line:
            question_start = i + 1
            break
    
    if question_start == 0:
        # No metadata found, assume entire input is the question
        return input_string.strip()
    else:
        return '\n'.join(lines[question_start:]).strip()

def solve_question(question_content: str, start_time: float, timeout: float) -> str:
    """Use LLM to solve the scientific question"""
    
    system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, astronomy, mathematics, and other scientific fields. You excel at solving complex multiple choice questions with careful step-by-step reasoning."""
    
    prompt = f"""Solve this scientific multiple choice question step by step:

{question_content}

Instructions:
1. Carefully read and understand what is being asked
2. Identify the scientific domain and relevant principles
3. Show your step-by-step reasoning, including any calculations
4. For physics problems, apply appropriate formulas and constants
5. For chemistry problems, consider reaction mechanisms and structures
6. For astronomy problems, use relevant astrophysical concepts
7. At the very end, clearly state "Answer: <letter>" where <letter> is A, B, C, or D

Be thorough in your analysis but concise in your explanation."""

    # Check timeout before LLM call
    if time.time() - start_time > timeout:
        logging.warning("Timeout reached before LLM call")
        return "A"
    
    try:
        logging.info("Calling LLM to solve question")
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Extract answer from response
        answer = extract_answer_letter(response)
        return answer
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"

def extract_answer_letter(response: str) -> str:
    """Extract the final answer letter from LLM response"""
    
    # Primary pattern: "Answer: X" (case insensitive)
    answer_pattern = r'Answer:\s*([ABCD])'
    matches = re.findall(answer_pattern, response, re.IGNORECASE)
    
    if matches:
        return matches[-1].upper()  # Take the last match
    
    # Secondary patterns to try
    patterns = [
        r'final answer is\s*([ABCD])',
        r'answer is\s*([ABCD])',
        r'correct answer is\s*([ABCD])',
        r'therefore\s*([ABCD])',
        r'thus\s*([ABCD])',
        r'option\s*([ABCD])',
        r'choice\s*([ABCD])',
        r'\b([ABCD])\s*is\s*(correct|right)',
        r'the answer should be\s*([ABCD])'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    
    # Look for isolated answer letters in the conclusion
    # Split into sentences and check the last few
    sentences = re.split(r'[.!?]', response)
    
    for sentence in reversed(sentences[-5:]):  # Check last 5 sentences
        isolated_letters = re.findall(r'\b([ABCD])\b', sentence.upper())
        if isolated_letters:
            return isolated_letters[-1]
    
    # Last resort: look for any letter pattern in the entire response
    all_letters = re.findall(r'\b([ABCD])\b', response.upper())
    if all_letters:
        # Return the most frequently occurring letter, or the last one if tied
        from collections import Counter
        letter_counts = Counter(all_letters)
        return letter_counts.most_common(1)[0][0]
    
    # Ultimate fallback
    logging.warning("Could not extract answer letter from response, defaulting to A")
    return "A"