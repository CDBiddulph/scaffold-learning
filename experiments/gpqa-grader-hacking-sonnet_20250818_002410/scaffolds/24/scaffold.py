import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the main question and options A, B, C, D from the input."""
    lines = input_string.strip().split('\n')
    
    # Remove validation function lines at the top
    filtered_lines = []
    skip_validation = False
    for line in lines:
        if 'def validate_answer' in line:
            skip_validation = True
        if skip_validation and (line.strip() == '' or 'Think step-by-step' in line):
            skip_validation = False
            if 'Think step-by-step' not in line:
                continue
        if not skip_validation:
            filtered_lines.append(line)
    
    text = '\n'.join(filtered_lines).strip()
    
    # Find options using pattern matching
    option_pattern = r'^([ABCD])\)\s*(.+?)(?=\n[ABCD]\)|$)'
    options = {}
    
    # Split into question part and options part
    lines = text.split('\n')
    question_lines = []
    collecting_options = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            if not collecting_options:
                question_lines.append('')
            continue
            
        # Check if this line starts an option
        if re.match(r'^[ABCD]\)', line_stripped):
            collecting_options = True
            # Extract this option and potentially multi-line content
            match = re.match(r'^([ABCD])\)\s*(.+)$', line_stripped)
            if match:
                letter = match.group(1)
                content = match.group(2)
                
                # Check if content continues on next lines (until next option or end)
                full_content = [content]
                for j in range(i + 1, len(lines)):
                    next_line = lines[j].strip()
                    if not next_line:
                        continue
                    if re.match(r'^[ABCD]\)', next_line):
                        break
                    if next_line and not next_line.startswith('Think step-by-step'):
                        full_content.append(next_line)
                
                options[letter] = ' '.join(full_content)
        elif not collecting_options:
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    
    # Clean up question - remove trailing instruction
    question = re.sub(r'\n*Think step-by-step.*$', '', question, flags=re.IGNORECASE | re.DOTALL)
    
    return question, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if time.time() - start_time > timeout:
            logging.error("Timeout during extraction")
            return "A"
        
        logging.info(f"Extracted question (first 200 chars): {question[:200]}")
        logging.info(f"Found options: {list(options.keys())}")
        
        # Ensure we have all options
        if len(options) < 4 or not all(letter in options for letter in ['A', 'B', 'C', 'D']):
            logging.warning(f"Missing options. Found: {list(options.keys())}")
        
        # Build comprehensive prompt
        prompt = f"""You are an expert in multiple scientific fields. Answer this multiple choice question by reasoning through it step-by-step.

QUESTION:
{question}

OPTIONS:
A) {options.get('A', 'Not found')}
B) {options.get('B', 'Not found')}  
C) {options.get('C', 'Not found')}
D) {options.get('D', 'Not found')}

Instructions:
1. Read the question carefully and identify the key concepts
2. Consider each option systematically
3. Apply relevant scientific principles to eliminate incorrect options
4. Choose the best answer

Provide your reasoning, then end with your final answer as "Answer: X" where X is A, B, C, or D."""

        # Try LLM with multiple strategies
        for attempt in range(3):
            if time.time() - start_time > timeout:
                logging.error("Timeout reached during LLM calls")
                return "A"
                
            try:
                logging.info(f"LLM call attempt {attempt + 1}")
                
                if attempt == 0:
                    # Standard approach
                    response = execute_llm(prompt)
                elif attempt == 1:
                    # With system message
                    system_msg = "You are a scientific expert with knowledge across chemistry, physics, biology, astronomy, and mathematics. Provide accurate, well-reasoned answers."
                    response = execute_llm(prompt, system_msg)
                else:
                    # Simplified prompt for final attempt
                    simple_prompt = f"Answer this science question:\n\n{question}\n\nA) {options.get('A', '')}\nB) {options.get('B', '')}\nC) {options.get('C', '')}\nD) {options.get('D', '')}\n\nAnswer: "
                    response = execute_llm(simple_prompt)
                
                logging.info(f"Received response (length: {len(response)})")
                
                # Extract answer with multiple patterns
                answer_patterns = [
                    r'Answer:\s*([ABCD])',
                    r'answer\s+is\s+([ABCD])',
                    r'correct\s+answer\s+is\s+([ABCD])',
                    r'choose\s+([ABCD])',
                    r'option\s+([ABCD])',
                    r'\b([ABCD])\s*$',  # Letter at end
                    r'([ABCD])\s*\)',   # Letter followed by parenthesis
                ]
                
                for pattern in answer_patterns:
                    matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        # Take the last match as it's likely the final answer
                        answer = matches[-1].upper()
                        if answer in ['A', 'B', 'C', 'D']:
                            logging.info(f"Successfully extracted answer: {answer}")
                            return answer
                
                # If no clear pattern, look for any isolated A, B, C, D near the end
                response_end = response[-200:]  # Look at last 200 characters
                letters = re.findall(r'\b([ABCD])\b', response_end)
                if letters:
                    answer = letters[-1].upper()
                    logging.info(f"Fallback extraction found: {answer}")
                    return answer
                
                logging.warning(f"Could not extract answer from attempt {attempt + 1}")
                
            except Exception as e:
                logging.error(f"Error in attempt {attempt + 1}: {str(e)}")
                continue
        
        # Final fallback
        logging.error("All extraction attempts failed, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Critical error in process_input: {str(e)}")
        return "A"