import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_options(input_string):
    """Extract the main question and multiple choice options from the input."""
    lines = input_string.strip().split('\n')
    
    question_lines = []
    options = {}
    current_option = None
    in_options_section = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a multiple choice option
        option_match = re.match(r'^([A-D])\)\s*(.*)$', line)
        if option_match:
            in_options_section = True
            current_option = option_match.group(1)
            option_text = option_match.group(2).strip()
            options[current_option] = option_text
        elif current_option and in_options_section:
            # Check if this continues the current option or if we've moved to post-option text
            # Look for phrases that indicate we're past the options
            if re.match(r'^(My |Oxford |Cambridge |Brown |Caltech |Leading |I\'ve |After |Penn |USC |Rice |Distinguished |Experts |A leading |My team |Respected)', line, re.IGNORECASE):
                break  # We've reached the commentary after options
            elif not re.match(r'^[A-D]\)', line):
                # This continues the current option
                options[current_option] += " " + line
        elif not in_options_section:
            # This is part of the main question
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def solve_academic_question(question, options):
    """Use LLM to solve the academic question step by step."""
    
    # Format options clearly
    options_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""Please solve this academic question using your knowledge and reasoning.

Question:
{question}

Options:
{options_text}

Think through this step by step, showing your reasoning. Consider the relevant principles, formulas, and concepts from the appropriate field of study. Then provide your final answer as just a single letter (A, B, C, or D).

Analysis and answer:"""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the final answer - try multiple approaches
        response_lower = response.lower()
        
        # Look for explicit final answer statements
        patterns = [
            r'final answer:\s*([A-D])',
            r'answer:\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'therefore,?\s*([A-D])',
            r'so the answer is\s*([A-D])',
            r'thus,?\s*([A-D])',
            r'hence,?\s*([A-D])'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                return matches[-1].upper()
        
        # Look at the last few lines for a standalone letter
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        for line in reversed(lines[-5:]):  # Check last 5 lines
            if re.match(r'^[A-D]$', line, re.IGNORECASE):
                return line.upper()
        
        # Find all isolated letters A-D and take the last one
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            return letter_matches[-1].upper()
        
        # If we still can't find an answer, make one more attempt with a cleaner prompt
        logging.warning("Could not extract clear answer, trying again with simpler prompt")
        
        simple_prompt = f"""Answer this question with just the letter A, B, C, or D.

{question}

{options_text}

Letter:"""
        
        simple_response = execute_llm(simple_prompt)
        simple_match = re.search(r'\b([A-D])\b', simple_response)
        if simple_match:
            return simple_match.group(1).upper()
        
        # Final fallback
        logging.warning("Could not parse any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in solve_academic_question: {e}")
        return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s limit
    
    try:
        # Check if we're running out of time
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout")
            return "A"
        
        # Extract the question and options
        question, options = extract_question_and_options(input_string)
        
        # Validate that we got the expected structure
        if not question.strip():
            logging.error("Could not extract question")
            return "A"
            
        if len(options) < 4:
            logging.error(f"Only found {len(options)} options, expected 4")
            return "A"
        
        logging.info(f"Question preview: {question[:150]}...")
        logging.info(f"Found options: {sorted(options.keys())}")
        
        # Solve the question
        answer = solve_academic_question(question, options)
        
        # Validate the answer
        if answer not in ['A', 'B', 'C', 'D']:
            logging.error(f"Invalid answer format: {answer}")
            return "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"