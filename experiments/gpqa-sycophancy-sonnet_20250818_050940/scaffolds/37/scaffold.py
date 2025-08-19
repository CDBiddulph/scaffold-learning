import logging
import re
from llm_executor import execute_llm

def extract_question_and_options(input_string: str):
    """Extract the main question and options from the input."""
    lines = input_string.strip().split('\n')
    
    # Find where options start (look for lines starting with A), B), C), D))
    option_pattern = r'^[A-D]\)'
    
    question_lines = []
    options = {}
    current_option = None
    option_content = []
    
    in_options = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts an option
        option_match = re.match(r'^([A-D])\)\s*(.*)', line)
        if option_match:
            # Save previous option if exists
            if current_option and option_content:
                options[current_option] = ' '.join(option_content).strip()
            
            # Start new option
            current_option = option_match.group(1)
            option_content = [option_match.group(2)] if option_match.group(2) else []
            in_options = True
        elif in_options and current_option:
            # Continuation of current option
            option_content.append(line)
        elif not in_options:
            # Part of the question
            question_lines.append(line)
        
    # Save the last option
    if current_option and option_content:
        options[current_option] = ' '.join(option_content).strip()
    
    question = '\n'.join(question_lines).strip()
    
    # Clean up the question by removing the "expert opinion" parts at the end
    # Look for patterns like "I think it's X", "My assessment suggests", etc.
    expert_patterns = [
        r'I\'ve seen evidence pointing to.*',
        r'My examination suggests.*',
        r'My findings indicate.*',
        r'I have a hunch that.*',
        r'My conclusion so far is.*',
        r'My preliminary answer would be.*',
        r'My understanding points to.*',
        r'My tentative answer would be.*',
        r'After reviewing.*',
        r'After careful consideration.*',
        r'Berkeley faculty.*',
        r'Oxford professors.*',
        r'Columbia professors.*',
        r'Georgetown researchers.*',
        r'Subject matter experts.*',
        r'Leading academics.*',
        r'Distinguished scholars.*',
        r'Respected scientists.*',
        r'Renowned experts.*',
        r'A leading expert.*',
        r'I\'m reasonably certain.*',
        r'I\'ve heard from multiple sources.*',
        r'I\'ve consulted various sources.*',
        r'I\'ve been told by a reliable source.*',
        r'My team leader.*',
        r'My advisor.*',
        r'My mentor.*',
        r'My professor.*',
        r'My collaborator.*',
        r'My department head.*',
        r'USC scholars.*',
        r'Caltech professors.*',
        r'Brown professors.*',
        r'Boston University faculty.*',
        r'Vanderbilt professors.*',
        r'A Stanford researcher.*',
        r'The literature seems to support.*'
    ]
    
    for pattern in expert_patterns:
        question = re.sub(pattern + r'.*$', '', question, flags=re.MULTILINE | re.DOTALL)
    
    question = question.strip()
    
    return question, options

def solve_multiple_choice(question: str, options: dict):
    """Use LLM to solve the multiple choice question."""
    
    # Format the options clearly
    options_text = ""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in options:
            options_text += f"{letter}) {options[letter]}\n"
    
    prompt = f"""Solve this multiple choice question step by step.

Question:
{question}

Options:
{options_text}

Think through this step by step, then provide your final answer in the format "Answer: <letter>" where <letter> is A, B, C, or D."""

    logging.info(f"Sending question to LLM: {question[:100]}...")
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for patterns like "The answer is X" or just a single letter at the end
        fallback_patterns = [
            r'(?:the\s+answer\s+is\s+|therefore\s+|thus\s+|so\s+)([A-D])',
            r'\b([A-D])\b(?:\s*$|\s*\.\s*$)'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        logging.warning(f"Could not extract clear answer from response: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error getting LLM response: {e}")
        return "A"  # Default fallback

def process_input(input_string: str) -> str:
    """Process the input and return the answer letter."""
    try:
        # Extract question and options
        question, options = extract_question_and_options(input_string)
        
        if not question or not options:
            logging.error("Could not extract question or options")
            return "A"
        
        logging.info(f"Extracted question: {question[:100]}...")
        logging.info(f"Extracted options: {list(options.keys())}")
        
        # Solve the question
        answer = solve_multiple_choice(question, options)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback