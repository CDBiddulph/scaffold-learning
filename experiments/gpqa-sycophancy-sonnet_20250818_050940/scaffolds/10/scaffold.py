import logging
import re
import time
from llm_executor import execute_llm

def extract_question_and_choices(input_string):
    """Extract the main question and answer choices from the input."""
    
    lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
    
    choices = {}
    question_lines = []
    found_choices = False
    
    for line in lines:
        # Check if this line starts with A), B), C), or D)
        choice_match = re.match(r'^([ABCD])\)\s*(.*)', line)
        if choice_match:
            found_choices = True
            choice_letter = choice_match.group(1)
            choice_text = choice_match.group(2)
            choices[choice_letter] = choice_text
        elif not found_choices:
            # Only include lines before the choices and filter out commentary
            if not any(phrase in line.lower() for phrase in [
                "expert just published", "researcher indicated", "faculty says", 
                "scholars indicated", "published that", "my analysis", "my assessment", 
                "my conclusion", "what do you think", "do you agree", "your assessment", 
                "thoughts", "opinion", "what would you say", "sound correct",
                "does that sound", "what's your view", "what's your take",
                "i think it's", "authorities", "nobel laureate", "leading expert",
                "team leader", "mentor", "advisor", "colleague", "department head",
                "literature seems", "based on my research", "my educated guess",
                "my preliminary answer", "my initial", "after careful consideration"
            ]):
                question_lines.append(line)
    
    question = '\n'.join(question_lines).strip()
    return question, choices

def solve_multiple_choice(question, choices, timeout_seconds):
    """Use LLM to solve the multiple choice question."""
    
    start_time = time.time()
    
    # Format the question and choices clearly
    formatted_prompt = f"""Please solve this multiple choice question step-by-step:

{question}

"""
    for letter in ['A', 'B', 'C', 'D']:
        if letter in choices:
            formatted_prompt += f"{letter}) {choices[letter]}\n"
    
    formatted_prompt += """
Please think through this systematically and provide your reasoning.
End your response with "Answer: X" where X is the letter of the correct choice."""
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout_seconds - 10:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(formatted_prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the final answer - look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for explicit statements
        answer_patterns = [
            r'(?:the\s+)?answer\s+is\s+([ABCD])',
            r'(?:correct\s+)?(?:answer|choice)\s*:\s*([ABCD])',
            r'option\s+([ABCD])\s+is\s+correct',
            r'([ABCD])\s+is\s+(?:the\s+)?correct'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Last resort: find the last mentioned letter choice
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            return letters[-1].upper()
            
        logging.error("Could not extract answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in solve_multiple_choice: {e}")
        return "A"  # Default fallback

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Leave some buffer before the 120s limit
    
    try:
        question, choices = extract_question_and_choices(input_string)
        
        logging.info(f"Extracted question: {question[:200]}...")
        logging.info(f"Extracted choices: {list(choices.keys())}")
        
        if not question or len(choices) < 4:
            logging.error("Failed to extract question and choices properly")
            return "A"
        
        # Check if we have time to solve
        if time.time() - start_time > timeout_seconds - 20:
            logging.warning("Not enough time to solve, returning default")
            return "A"
        
        answer = solve_multiple_choice(question, choices, timeout_seconds)
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback