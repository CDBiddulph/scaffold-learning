import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and multiple choice options from the input."""
    
    # Split into lines
    lines = input_string.strip().split('\n')
    
    # Find where options start
    option_start_idx = None
    options = {}
    
    for i, line in enumerate(lines):
        line = line.strip()
        if re.match(r'^A\)\s*', line):
            option_start_idx = i
            break
    
    if option_start_idx is None:
        logging.error("Could not find options starting with A)")
        return "", {}
    
    # Extract question (everything before options)
    question_lines = []
    for i in range(option_start_idx):
        line = lines[i].strip()
        if line:
            question_lines.append(line)
    
    question = ' '.join(question_lines)
    
    # Extract options - handle multi-line options
    current_option = None
    for i in range(option_start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
            
        option_match = re.match(r'^([A-D])\)\s*(.+)', line)
        if option_match:
            letter = option_match.group(1)
            content = option_match.group(2)
            options[letter] = content
            current_option = letter
        elif current_option and line and not re.match(r'^[A-D]\)', line):
            # This might be a continuation of the previous option
            # But stop if we hit commentary text
            if not any(indicator in line.lower() for indicator in [
                "i think", "my", "experts", "scholars", "authorities", 
                "suggested", "indicated", "told me", "what do you think",
                "sound correct", "your assessment", "thoughts"
            ]):
                options[current_option] += ' ' + line
            else:
                break  # Stop processing when we hit commentary
    
    return question, options

def solve_scientific_question(question, options):
    """Use LLM to solve the scientific question."""
    
    # Format the options nicely
    options_text = "\n".join([f"{letter}) {content}" for letter, content in sorted(options.items())])
    
    prompt = f"""You are a scientific expert across multiple domains. Analyze this question step by step.

Question: {question}

Options:
{options_text}

Please:
1. Identify the scientific domain and key concepts
2. Analyze what the question is asking
3. Evaluate each option systematically 
4. Apply relevant scientific principles and knowledge
5. Determine the correct answer

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""

    response = execute_llm(prompt)
    return response

def extract_answer_letter(response):
    """Extract the final answer letter from the LLM response."""
    
    # Look for "Answer: X" pattern first (most reliable)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1)
    
    # Look for other common answer patterns
    patterns = [
        r'(?:the\s+answer\s+is|final\s+answer\s+is|therefore\s+the\s+answer\s+is|my\s+answer\s+is|conclusion\s+is)\s*([A-D])',
        r'([A-D])\s*(?:is\s+(?:the\s+)?correct|is\s+(?:the\s+)?answer)',
        r'(?:choose|select|pick)\s*(?:option\s*)?([A-D])',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Look for the last occurrence of a standalone letter near the end
    lines = response.split('\n')
    for line in reversed(lines[-10:]):  # Check last 10 lines
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
    
    # Look for any standalone letters in the response
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1]  # Return the last one found
    
    # If all else fails, return A as default
    logging.warning(f"Could not extract answer letter from response: {response[:300]}...")
    return 'A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120 second timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        logging.info(f"Extracted question length: {len(question)} chars")
        logging.info(f"Found {len(options)} options: {sorted(options.keys())}")
        
        if not question or len(options) < 4:
            logging.error(f"Failed to extract proper question/options. Q:{bool(question)}, Opts:{len(options)}")
            return 'A'
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return 'A'
        
        # Solve the question using LLM
        logging.info("Sending to LLM for analysis")
        response = solve_scientific_question(question, options)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer letter
        answer_letter = extract_answer_letter(response)
        logging.info(f"Extracted final answer: {answer_letter}")
        
        if answer_letter not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer letter: {answer_letter}, defaulting to A")
            return 'A'
        
        return answer_letter
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return 'A'