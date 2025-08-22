import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave buffer before 120 second limit
    
    try:
        logging.info("Starting to process scientific question")
        
        # Parse the question and answer choices
        question_text, choices = parse_question(input_string)
        
        if not choices:
            logging.error("No answer choices found, returning default A")
            return "A"
        
        logging.info(f"Question parsed, found {len(choices)} choices: {list(choices.keys())}")
        
        # Check timeout before expensive LLM call
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Use LLM to analyze the scientific question
        answer = analyze_with_llm(question_text, choices)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe default

def parse_question(input_string: str) -> tuple:
    """Parse input to extract question text and answer choices"""
    lines = input_string.strip().split('\n')
    
    choices = {}
    question_parts = []
    found_first_choice = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Look for answer choices with multiple patterns
        choice_patterns = [
            r'^([ABCD])\)\s*(.*)$',      # A) choice text
            r'^([ABCD])\s+(.*)$',        # A choice text  
            r'^([ABCD])[\.\:]?\s*(.*)$'  # A. or A: choice text
        ]
        
        choice_found = False
        for pattern in choice_patterns:
            match = re.match(pattern, line)
            if match:
                letter = match.group(1)
                text = match.group(2).strip()
                choices[letter] = text
                choice_found = True
                found_first_choice = True
                break
        
        if not choice_found and not found_first_choice:
            # This line is part of the question
            question_parts.append(line)
    
    question_text = '\n'.join(question_parts).strip()
    
    logging.info(f"Parsed question (length: {len(question_text)})")
    logging.info(f"Found choices: {sorted(choices.keys())}")
    
    return question_text, choices

def analyze_with_llm(question_text: str, choices: dict) -> str:
    """Use LLM to analyze the scientific question and determine correct answer"""
    
    # Construct a focused prompt for scientific analysis
    prompt = f"""You are a scientific expert with deep knowledge across multiple domains including biology, chemistry, physics, astronomy, and related fields.

Analyze this multiple-choice question carefully and determine the correct answer.

Question:
{question_text}

Answer Choices:
"""
    
    for letter in sorted(choices.keys()):
        prompt += f"{letter}) {choices[letter]}\n"
    
    prompt += """

Please think step-by-step through this problem:
1. Identify the key scientific concepts involved
2. Apply relevant scientific principles and knowledge
3. Evaluate each answer choice systematically
4. Determine which choice is most accurate

Conclude your analysis with "Answer: <letter>" where <letter> is A, B, C, or D.
"""
    
    try:
        logging.info("Calling LLM for scientific analysis")
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([ABCD])',
            r'answer:\s*([ABCD])', 
            r'Answer\s*=\s*([ABCD])',
            r'Final answer:\s*([ABCD])',
            r'The answer is\s*([ABCD])',
            r'Choice\s*([ABCD])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Successfully extracted answer: {answer}")
                return answer
        
        # Fallback: look for isolated letters at the end of response
        words = response.strip().split()
        for word in reversed(words[-5:]):  # Check last few words
            clean_word = re.sub(r'[^\w]', '', word).upper()
            if clean_word in ['A', 'B', 'C', 'D'] and len(clean_word) == 1:
                logging.info(f"Found fallback answer: {clean_word}")
                return clean_word
        
        # Last resort: look for any single letter in the response
        single_letters = re.findall(r'\b([ABCD])\b', response)
        if single_letters:
            answer = single_letters[-1]  # Take the last occurrence
            logging.info(f"Found last resort answer: {answer}")
            return answer
        
        logging.warning("Could not extract any answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in LLM analysis: {e}")
        return "A"