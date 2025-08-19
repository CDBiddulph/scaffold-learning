import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_choices(input_string):
    """Extract the question and multiple choice options from the input."""
    # Clean up HTML entities
    input_string = input_string.replace('&lt;', '<').replace('&gt;', '>')
    
    # Find the multiple choice options
    choice_pattern = re.compile(r'^([A-D])\)\s*(.+)$', re.MULTILINE)
    choices = {}
    choice_positions = []
    
    for match in choice_pattern.finditer(input_string):
        letter = match.group(1)
        text = match.group(2).strip()
        choices[letter] = text
        choice_positions.append(match.start())
    
    # Extract question - everything before the first choice
    if choice_positions:
        question_end = choice_positions[0]
        question = input_string[:question_end].strip()
    else:
        # Fallback approach
        lines = input_string.strip().split('\n')
        question_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Stop at expert opinion indicators or instructions
            if re.search(r'(I have a hunch|told me|assessment|experts|professors|believe|confident|opinion|thoughts|view|agree|concur|researchers|authorities|Cambridge|MIT|Duke|Stanford|Berkeley|Brown|Columbia|Georgetown|Vanderbilt|Think step-by-step)', line, re.IGNORECASE):
                break
            question_lines.append(line)
        
        question = ' '.join(question_lines)
    
    return question, choices

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract question and choices  
        question, choices = extract_question_and_choices(input_string)
        
        if not question:
            logging.error("Failed to extract question")
            return "A"
            
        logging.info(f"Question extracted: {len(question)} characters")
        logging.info(f"Found {len(choices)} choices: {list(choices.keys())}")
        
        # Build choices text
        choices_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in choices:
                choices_text += f"{letter}) {choices[letter]}\n"
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer time
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        prompt = f"""Solve this multiple choice scientific question step-by-step.

Question: {question}

{choices_text}

Please think through this systematically using your scientific knowledge and provide your final answer in the exact format "Answer: X" where X is the correct letter (A, B, C, or D).
"""
        
        logging.info("Sending question to LLM...")
        
        # Get response from LLM
        response = execute_llm(prompt)
        
        # Extract answer from response using multiple patterns
        patterns = [
            re.compile(r'Answer:\s*([A-D])', re.IGNORECASE),
            re.compile(r'the\s+answer\s+is\s+([A-D])', re.IGNORECASE),
            re.compile(r'correct\s+answer.*?([A-D])', re.IGNORECASE),
            re.compile(r'choose\s+([A-D])', re.IGNORECASE),
            re.compile(r'option\s+([A-D])', re.IGNORECASE),
            re.compile(r'([A-D])\s*is\s+correct', re.IGNORECASE),
        ]
        
        for pattern in patterns:
            match = pattern.search(response)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Successfully extracted answer: {answer}")
                return answer
        
        # Last resort - find any isolated letter in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()  # Take the last one mentioned
            logging.info(f"Fallback answer: {answer}")
            return answer
        
        logging.error(f"Could not extract answer from response: {response[:200]}...")
        return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback