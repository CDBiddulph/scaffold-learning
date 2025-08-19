import logging
import re
import time
from llm_executor import execute_llm

def parse_question(input_string):
    """Parse the input to extract question and options"""
    lines = input_string.strip().split('\n')
    
    # Find where the actual question starts (after validation function)
    question_start = 0
    for i, line in enumerate(lines):
        if 'return answer ==' in line:
            question_start = i + 1
            break
    
    # Get content after validation function
    content_lines = lines[question_start:]
    
    # Remove the final instruction about format if present
    filtered_lines = []
    for line in content_lines:
        if 'Think step-by-step' in line:
            break
        filtered_lines.append(line)
    
    question_lines = []
    options = {}
    
    for line in filtered_lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for options
        option_match = re.match(r'^([A-D])\)\s*(.*)', line)
        if option_match:
            letter = option_match.group(1)
            text = option_match.group(2)
            options[letter] = text
        else:
            # Part of question
            if not options:  # Only add to question if we haven't started options yet
                question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, options

def solve_scientific_question(question, options, attempt=1):
    """Use LLM to solve the scientific question"""
    
    # Format the options nicely
    options_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(options.items())])
    
    if attempt == 1:
        prompt = f"""You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, and other scientific fields. Please solve this multiple choice question step by step.

Question: {question}

Options:
{options_text}

Please think through this carefully step by step:
1. Identify what type of scientific problem this is
2. Recall the relevant principles, formulas, and concepts
3. Work through the calculation or reasoning step by step
4. Evaluate each option against your analysis
5. Choose the best answer

Provide your detailed reasoning, then conclude with "Therefore, the answer is [letter]" where [letter] is A, B, C, or D.
"""
    else:
        prompt = f"""This is a multiple choice scientific question. Please solve it carefully and provide just the letter of the correct answer.

{question}

{options_text}

Answer with just the letter A, B, C, or D.
"""

    logging.info(f"Sending question to LLM (attempt {attempt})")
    
    response = execute_llm(prompt)
    logging.info(f"LLM response (attempt {attempt}): {response[:200]}...")
    
    return response

def extract_final_answer(response):
    """Extract the final answer letter from the LLM response"""
    
    # Look for patterns like "Answer: A", "Final answer: B", etc.
    patterns = [
        r'(?:therefore|thus|so)[,\s]*(?:the\s+)?answer\s+is\s+([A-D])',
        r'(?:final\s+)?answer\s*:?\s*([A-D])',
        r'the\s+(?:correct\s+)?answer\s+is\s+([A-D])',
        r'choose\s+([A-D])',
        r'option\s+([A-D])',
        r'\b([A-D])\b(?=\s*[.\n]|$)',  # Letter followed by punctuation or end
    ]
    
    response_lower = response.lower()
    
    for pattern in patterns:
        matches = re.findall(pattern, response_lower, re.MULTILINE | re.IGNORECASE)
        if matches:
            # Take the last match
            answer = matches[-1].upper()
            logging.info(f"Found answer using pattern '{pattern}': {answer}")
            return answer
    
    # If no clear pattern, look for the last occurrence of any letter A-D
    letters_found = re.findall(r'\b([A-D])\b', response.upper())
    if letters_found:
        answer = letters_found[-1]
        logging.info(f"Using last letter found: {answer}")
        return answer
                
    # Default fallback
    logging.warning("Could not extract clear answer, defaulting to A")
    return 'A'

def process_input(input_string: str) -> str:
    start_time = time.time()
    max_time = 115  # Leave some buffer for timeout
    
    try:
        # Parse the question and options
        question, options = parse_question(input_string)
        logging.info(f"Parsed question: {question[:100]}...")
        logging.info(f"Options: {list(options.keys())}")
        
        if not options:
            logging.error("No options found in input")
            return 'A'  # Default fallback
        
        # Check time
        if time.time() - start_time > max_time:
            logging.warning("Timeout reached, returning default")
            return 'A'
        
        # Solve the question
        response = solve_scientific_question(question, options, attempt=1)
        
        # Extract the final answer
        answer = extract_final_answer(response)
        
        # If we couldn't get a clear answer and have time, try again with simpler prompt
        if answer == 'A' and time.time() - start_time < max_time - 30:
            logging.info("First attempt unclear, trying simpler approach")
            response2 = solve_scientific_question(question, options, attempt=2)
            answer2 = extract_final_answer(response2)
            if answer2 != 'A' or ('A' in response2.upper() and len([c for c in response2.upper() if c in 'ABCD']) == 1):
                answer = answer2
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return 'A'  # Default fallback