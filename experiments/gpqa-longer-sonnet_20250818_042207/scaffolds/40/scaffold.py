import logging
import re
import time
import html
from llm_executor import execute_llm

def parse_question_and_options(input_string):
    """Parse the input to extract question and options"""
    # Decode HTML entities like &gt; -> >
    input_string = html.unescape(input_string)
    
    lines = input_string.strip().split('\n')
    
    # Find first line starting with A), B), C), or D)
    option_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^[A-D]\)', line.strip()):
            option_start = i
            break
    
    if option_start == -1:
        raise ValueError("Could not find options starting with A), B), C), or D)")
    
    # Question is everything before options, excluding instruction lines
    question_lines = lines[:option_start]
    question_lines = [line for line in question_lines 
                     if not line.strip().startswith("Think step-by-step")]
    question = '\n'.join(question_lines).strip()
    
    # Parse options
    option_lines = lines[option_start:]
    options = {}
    current_option = None
    current_text = []
    
    for line in option_lines:
        line = line.strip()
        if not line or line.startswith("Think step-by-step"):
            continue
            
        # Check if this starts a new option
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            # Save previous option
            if current_option:
                options[current_option] = ' '.join(current_text).strip()
            
            current_option = match.group(1)
            rest = match.group(2).strip()
            current_text = [rest] if rest else []
        else:
            # Continuation of current option
            if current_option:
                current_text.append(line)
    
    # Save last option
    if current_option:
        options[current_option] = ' '.join(current_text).strip()
    
    return question, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        question, options = parse_question_and_options(input_string)
        
        logging.info(f"Question length: {len(question)}")
        logging.info(f"Options found: {list(options.keys())}")
        
        # Check timeout before expensive LLM call
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Build focused prompt for scientific analysis
        prompt = f"""You are a scientific expert. Analyze this multiple-choice question step-by-step and determine the correct answer.

QUESTION:
{question}

OPTIONS:
"""
        
        for letter in sorted(options.keys()):
            prompt += f"{letter}) {options[letter]}\n"
        
        prompt += """\nThink through the scientific concepts involved, analyze each option, and provide your final answer in the format: "Answer: X" where X is A, B, C, or D."""
        
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'final answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'answer is\s*([A-D])',
            r'therefore\s*([A-D])',
            r'thus\s*([A-D])',
            r'so\s+([A-D])',
            r'option\s*([A-D])',
            r'\b([A-D])\s*is\s*correct',
            r'choose\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: look for isolated A-D letters in the final part of response
        final_section = response[-400:]  # Last 400 characters
        isolated_letters = re.findall(r'\b([A-D])\b', final_section)
        if isolated_letters:
            answer = isolated_letters[-1].upper()
            logging.info(f"Extracted answer '{answer}' from final section")
            return answer
        
        # Last resort: any A-D in entire response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Extracted answer '{answer}' as last resort")
            return answer
        
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"  # Safe fallback