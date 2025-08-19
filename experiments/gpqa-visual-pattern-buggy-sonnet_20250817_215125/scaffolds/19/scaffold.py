import logging
import re
import time
from llm_executor import execute_llm

def parse_question(input_string):
    """Parse the input to extract question and options."""
    lines = input_string.strip().split('\n')
    
    question_lines = []
    options = {}
    
    in_options = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is an option line (with possible ■ marker)
        option_match = re.match(r'^■?\s*([A-D])\)\s*(.+)', line)
        if option_match:
            in_options = True
            letter = option_match.group(1)
            text = option_match.group(2)
            options[letter] = text
        elif not in_options:
            question_lines.append(line)
    
    question = '\n'.join(question_lines)
    return question, options

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the question and options
        question, options = parse_question(input_string)
        
        if not question or len(options) == 0:
            logging.error("Failed to parse question or options")
            return "A"
        
        logging.info(f"Parsed question with {len(options)} options: {list(options.keys())}")
        
        # Check timeout buffer
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Format options for the LLM
        options_text = ""
        for letter in sorted(options.keys()):
            options_text += f"{letter}) {options[letter]}\n"
        
        # Create focused prompt for scientific reasoning
        prompt = f"""You are solving a scientific multiple-choice question. Think through this step-by-step using relevant scientific principles.

Question:
{question}

Options:
{options_text}

Analyze this problem systematically:
1. Identify the key scientific concepts involved
2. Apply relevant formulas, principles, or reasoning
3. Evaluate each option carefully
4. Select the best answer

Respond with your reasoning followed by your final answer as just the letter (A, B, C, or D)."""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer letter using multiple strategies
        # Strategy 1: Look for explicit answer statements
        answer_patterns = [
            r'(?:final\s+)?answer\s*:?\s*([A-D])',
            r'(?:correct\s+)?(?:option|choice)\s*:?\s*([A-D])',
            r'select\s*:?\s*([A-D])',
            r'therefore\s*:?\s*([A-D])',
            r'answer\s+is\s*:?\s*([A-D])',
            r'^([A-D])$',  # Just the letter on its own line
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer '{answer}' using pattern '{pattern}'")
                return answer
        
        # Strategy 2: Look for letters at the end of the response
        end_match = re.search(r'\b([A-D])\s*\.?\s*$', response, re.IGNORECASE | re.MULTILINE)
        if end_match:
            answer = end_match.group(1).upper()
            logging.info(f"Found answer '{answer}' at end of response")
            return answer
            
        # Strategy 3: Find all mentions of option letters and use the last one
        letters_found = re.findall(r'\b([A-D])\b', response)
        if letters_found:
            # Filter to only valid options we actually have
            valid_letters = [l for l in letters_found if l in options]
            if valid_letters:
                answer = valid_letters[-1]
                logging.info(f"Using last valid option mentioned: {answer}")
                return answer
        
        # Strategy 4: Parse for "option X is correct" type statements
        correct_pattern = re.search(r'option\s+([A-D])\s+is\s+correct', response, re.IGNORECASE)
        if correct_pattern:
            answer = correct_pattern.group(1).upper()
            logging.info(f"Found 'option X is correct' statement: {answer}")
            return answer
        
        # Final fallback
        logging.warning("Could not extract answer from response, using default A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"