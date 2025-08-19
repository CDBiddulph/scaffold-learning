import logging
import re
import time
from llm_executor import execute_llm

def parse_question_and_choices(input_string):
    """Extract question text and answer choices from input."""
    lines = input_string.strip().split('\n')
    
    # Find answer choice lines (A), B), C), D))
    choice_pattern = r'^[■\s]*([A-D])\)\s*(.*)$'
    choices = {}
    question_lines = []
    
    # Find where choices start
    choice_start_idx = None
    for i, line in enumerate(lines):
        if re.match(choice_pattern, line.strip()):
            if choice_start_idx is None:
                choice_start_idx = i
            # Extract this choice
            match = re.match(choice_pattern, line.strip())
            if match:
                letter = match.group(1)
                text = match.group(2).strip()
                choices[letter] = text
    
    # Question is everything before choices start
    if choice_start_idx is not None:
        for i in range(choice_start_idx):
            line = lines[i].strip()
            if line and not line.startswith("Think step-by-step"):
                question_lines.append(line)
    else:
        # No choices found, treat entire input as question
        question_lines = [line.strip() for line in lines if line.strip()]
    
    question = '\n'.join(question_lines).strip()
    return question, choices

def solve_scientific_question(question, choices):
    """Use LLM to solve the scientific question."""
    
    if not choices:
        # Open-ended question
        return execute_llm(question)
    
    # Format choices for the prompt
    choice_lines = []
    for letter in ['A', 'B', 'C', 'D']:
        if letter in choices:
            choice_lines.append(f"{letter}) {choices[letter]}")
    choices_text = '\n'.join(choice_lines)
    
    system_prompt = """You are a world-class expert scientist with comprehensive knowledge across all scientific disciplines including physics, chemistry, biology, astronomy, mathematics, geology, materials science, and more. You excel at solving complex multi-step problems that require both theoretical knowledge and quantitative analysis."""
    
    prompt = f"""Please solve this scientific problem step by step:

{question}

Answer choices:
{choices_text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""

    response = execute_llm(prompt, system_prompt)
    return response

def extract_answer_letter(response):
    """Extract the final answer letter from LLM response."""
    
    # Primary: Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Secondary: Look for conclusive statements
    response_lower = response.lower()
    for letter in ['A', 'B', 'C', 'D']:
        patterns = [
            f'the answer is {letter.lower()}',
            f'answer is {letter.lower()}',
            f'choose {letter.lower()}',
            f'{letter.lower()} is correct',
            f'{letter.lower()} is the answer',
            f'option {letter.lower()} is',
            f'select {letter.lower()}'
        ]
        
        for pattern in patterns:
            if pattern in response_lower:
                logging.info(f"Found answer {letter} using pattern: {pattern}")
                return letter
    
    # Tertiary: Find the last mentioned choice letter
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    # Fallback
    logging.warning(f"Could not extract answer from response: {response[:200]}...")
    return "A"

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse input
        question, choices = parse_question_and_choices(input_string)
        
        if not question:
            logging.error("No question found in input")
            return "A"
        
        logging.info(f"Question length: {len(question)} chars")
        logging.info(f"Choices found: {list(choices.keys()) if choices else 'None'}")
        
        # Check for timeout
        if time.time() - start_time > 100:  # Leave buffer for safety
            logging.warning("Approaching timeout")
            return "A"
        
        # Solve the question
        response = solve_scientific_question(question, choices)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # For multiple choice, extract the letter
        if choices:
            answer = extract_answer_letter(response)
            logging.info(f"Final answer: {answer}")
            return answer
        else:
            # For open-ended questions, return the full response
            return response.strip()
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"