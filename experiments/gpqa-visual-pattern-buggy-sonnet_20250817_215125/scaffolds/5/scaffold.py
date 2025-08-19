import logging
import re
import time
from llm_executor import execute_llm
from typing import Dict, Tuple

def extract_question_and_options(input_string: str) -> Tuple[str, Dict[str, str]]:
    """Extract the main question and the multiple choice options"""
    lines = input_string.strip().split('\n')
    
    question_lines = []
    options = {}
    current_option = None
    in_options = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove the ■ symbol if present (indicates correct answer in examples)
        line = re.sub(r'^■\s*', '', line)
        
        # Check if this line starts an option
        match = re.match(r'^([A-D])\)\s*(.*)', line)
        if match:
            in_options = True
            current_option = match.group(1)
            options[current_option] = match.group(2).strip()
        elif current_option and in_options and line and not re.match(r'^[A-D])\s', line):
            # Continuation of current option
            options[current_option] += ' ' + line
        elif not in_options:
            # Part of the question
            question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def solve_scientific_question(question: str, options: Dict[str, str]) -> str:
    """Solve a scientific multiple choice question using LLM reasoning"""
    
    # Format the question and options for the LLM
    formatted_options = '\n'.join([f"{key}) {value}" for key, value in sorted(options.items())])
    
    prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering.

Analyze this multiple choice question step by step:

Question:
{question}

Options:
{formatted_options}

Instructions:
1. Read the question carefully and identify the key scientific concepts
2. Think through the problem step by step
3. Evaluate each option systematically  
4. Apply relevant scientific principles, formulas, or reasoning
5. Select the best answer

Provide your step-by-step reasoning, then conclude with "Answer: X" where X is the correct letter."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM reasoning complete")
        
        # Extract the final answer - look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback patterns to find the answer
        fallback_patterns = [
            r'(?:the\s*)?(?:correct\s*)?answer\s*is\s*([A-D])',
            r'(?:option\s*)?([A-D])\s*is\s*(?:the\s*)?correct',
            r'(?:choose|select)\s*(?:option\s*)?([A-D])',
            r'([A-D])\s*is\s*(?:the\s*)?(?:best|right)\s*(?:answer|choice|option)',
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                return matches[-1].upper()
        
        logging.warning("Could not extract clear answer from response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in LLM execution: {e}")
        return "A"

def process_input(input_string: str) -> str:
    """Main function to process the input and return the answer"""
    start_time = time.time()
    
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        logging.info(f"Extracted question length: {len(question)}")
        logging.info(f"Found {len(options)} options: {list(options.keys())}")
        
        # Validate we have a reasonable question and options
        if not question.strip():
            logging.warning("No clear question found, using entire input")
            question = input_string
            
        if len(options) < 2:
            logging.warning("Insufficient options found, attempting to re-parse")
            # Try a more aggressive parsing approach
            lines = input_string.strip().split('\n')
            for line in lines:
                match = re.search(r'\b([A-D])\)', line)
                if match and match.group(1) not in options:
                    options[match.group(1)] = line.split(')', 1)[1].strip() if ')' in line else line
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave some buffer
            logging.warning("Approaching timeout")
            return "A"
        
        # Solve the question
        answer = solve_scientific_question(question, options)
        
        # Validate the answer is one of the available options
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer {answer}, defaulting to A")
            answer = "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback