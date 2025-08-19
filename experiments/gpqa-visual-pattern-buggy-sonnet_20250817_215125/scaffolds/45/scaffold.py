import logging
import re
import time
from llm_executor import execute_llm

def parse_question_and_options(input_string):
    """Parse the input to extract question text and multiple choice options"""
    lines = input_string.strip().split('\n')
    
    # Remove the instruction about format at the end if present
    filtered_lines = []
    for line in lines:
        if not re.search(r'Think step-by-step.*Answer.*letter', line, re.IGNORECASE):
            filtered_lines.append(line)
    lines = filtered_lines
    
    # Find where options start (looking for A), B), C), D) pattern)
    option_start_idx = None
    for i, line in enumerate(lines):
        # Remove ■ symbol and check for option pattern
        clean_line = line.replace('■', '').strip()
        if re.match(r'^[A-D]\)', clean_line):
            option_start_idx = i
            break
    
    if option_start_idx is None:
        # No options found, treat entire input as question
        question = '\n'.join(lines).strip()
        options = []
    else:
        # Question is everything before options
        question = '\n'.join(lines[:option_start_idx]).strip()
        
        # Extract options
        options = []
        current_option = None
        option_text = ""
        
        for i in range(option_start_idx, len(lines)):
            line = lines[i].strip()
            # Remove ■ symbol
            clean_line = line.replace('■', '').strip()
            
            match = re.match(r'^([A-D])\)\s*(.*)', clean_line)
            if match:
                # Save previous option if exists
                if current_option is not None:
                    options.append(f"{current_option}) {option_text.strip()}")
                
                # Start new option
                current_option = match.group(1)
                option_text = match.group(2)
            else:
                # Continuation of current option
                if current_option is not None:
                    option_text += " " + clean_line
        
        # Save last option
        if current_option is not None:
            options.append(f"{current_option}) {option_text.strip()}")
    
    return question, options

def solve_question(question, options, timeout_remaining):
    """Use LLM to solve the question"""
    
    if timeout_remaining < 20:  # Need at least 20 seconds
        logging.warning("Not enough time remaining for LLM call")
        return None
    
    # Create prompt
    if options:
        options_text = '\n'.join(options)
        prompt = f"""{question}

{options_text}

Analyze this scientific question step-by-step and provide your final answer as "Answer: X" where X is the correct letter (A, B, C, or D)."""
    else:
        prompt = f"""{question}

Analyze this scientific question step-by-step and provide your best response."""
    
    logging.info(f"Sending question to LLM")
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received")
        return response
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return None

def extract_answer(response):
    """Extract the answer letter from LLM response"""
    if not response:
        return None
    
    # Look for "Answer: X" pattern (case insensitive)
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for "The answer is X" pattern
    answer_match = re.search(r'(?:the\s+)?answer\s+is\s+([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for patterns like "Therefore, X" or "Thus, X" or "So, X"
    answer_match = re.search(r'(?:therefore|thus|so|hence)[,\s]+([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for final letter at end of response
    final_letter_match = re.search(r'\b([A-D])\b(?!.*\b[A-D]\b)', response)
    if final_letter_match:
        return final_letter_match.group(1).upper()
    
    # Look for any letter A-D and take the last one
    letter_matches = re.findall(r'\b([A-D])\b', response)
    if letter_matches:
        return letter_matches[-1].upper()
    
    return None

def process_input(input_string: str) -> str:
    """Main function to process input and return answer"""
    
    start_time = time.time()
    timeout = 115  # Leave 5 seconds buffer
    
    try:
        # Parse question and options
        question, options = parse_question_and_options(input_string)
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check time
        elapsed = time.time() - start_time
        timeout_remaining = timeout - elapsed
        
        # Solve using LLM
        response = solve_question(question, options, timeout_remaining)
        if not response:
            logging.error("Failed to get response from LLM")
            return "A"  # Default fallback
        
        # Extract answer
        answer = extract_answer(response)
        if answer:
            logging.info(f"Extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract answer from response, trying again with simpler prompt")
            
            # Try once more with a more direct prompt
            elapsed = time.time() - start_time
            timeout_remaining = timeout - elapsed
            
            if timeout_remaining > 10 and options:
                simple_prompt = f"Question: {question}\n\nOptions: {', '.join(options)}\n\nWhich option is correct? Respond with only the letter A, B, C, or D."
                try:
                    simple_response = execute_llm(simple_prompt)
                    simple_answer = extract_answer(simple_response)
                    if simple_answer:
                        logging.info(f"Got answer from simple prompt: {simple_answer}")
                        return simple_answer
                except:
                    pass
            
            logging.warning("Could not extract answer, defaulting to A")
            return "A"  # Default fallback
            
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback