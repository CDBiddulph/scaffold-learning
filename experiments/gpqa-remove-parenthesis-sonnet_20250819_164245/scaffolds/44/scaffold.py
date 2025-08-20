import logging
import re
import time
from typing import Optional, Tuple, Dict
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and choices
        question_text, choices = parse_question(input_string)
        logging.info(f"Parsed question with {len(choices)} choices")
        
        # Check time limit - leave buffer for processing
        if time.time() - start_time > 100:
            logging.warning("Approaching time limit")
            return "A"  # Default fallback
            
        # Get answer from LLM
        answer_letter = get_answer_from_llm(question_text, choices, start_time)
        logging.info(f"Final answer: {answer_letter}")
        
        return answer_letter
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def parse_question(input_string: str) -> Tuple[str, Dict[str, str]]:
    """Parse the input to extract question text and answer choices."""
    lines = [line.rstrip() for line in input_string.strip().split('\n')]
    
    # Find where the choices start - look for pattern like "A)" or "A " at start of line
    choice_pattern = re.compile(r'^[A-D][\)\s]')
    choice_start_idx = None
    
    for i, line in enumerate(lines):
        if choice_pattern.match(line):
            choice_start_idx = i
            break
    
    if choice_start_idx is None:
        # Try to find choices with different formatting
        for i, line in enumerate(lines):
            if line.strip().startswith(('A)', 'B)', 'C)', 'D)', 'A ', 'B ', 'C ', 'D ')):
                choice_start_idx = i
                break
    
    if choice_start_idx is None:
        raise ValueError("Could not find answer choices in input")
    
    # Question is everything before the choices
    question_lines = lines[:choice_start_idx]
    question_text = '\n'.join(question_lines).strip()
    
    # Parse choices
    choices = {}
    choice_lines = lines[choice_start_idx:]
    
    current_choice = None
    current_text = ""
    
    for line in choice_lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new choice
        match = re.match(r'^([A-D])[\)\s]?\s*(.*)', line)
        if match:
            # Save previous choice if exists
            if current_choice and current_text:
                choices[current_choice] = current_text.strip()
            
            current_choice = match.group(1)
            current_text = match.group(2)
        else:
            # This is a continuation of the current choice
            if current_choice:
                current_text += " " + line
    
    # Don't forget the last choice
    if current_choice and current_text:
        choices[current_choice] = current_text.strip()
    
    if len(choices) < 2:
        raise ValueError(f"Found only {len(choices)} answer choices")
    
    return question_text, choices

def get_answer_from_llm(question_text: str, choices: Dict[str, str], start_time: float) -> str:
    """Get the answer from the LLM with detailed analysis."""
    
    # Format the choices clearly
    choices_text = ""
    for letter in sorted(choices.keys()):
        choices_text += f"{letter}) {choices[letter]}\n"
    
    # Create a comprehensive prompt
    prompt = f"""You are an expert in multiple scientific fields including physics, chemistry, astronomy, and biology. Please analyze this technical multiple-choice question carefully.

Question:
{question_text}

Answer choices:
{choices_text}

Please approach this systematically:
1. Identify the key concepts and scientific principles involved
2. Work through the problem step-by-step with clear reasoning
3. Eliminate obviously incorrect answers
4. Choose the best answer based on scientific principles

End your response with exactly this format: "FINAL_ANSWER: X" where X is the letter of your chosen answer."""

    try:
        # Check time limit before making LLM call
        if time.time() - start_time > 90:
            logging.warning("Time limit approaching, using fallback")
            return 'A'
        
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the final answer
        answer_letter = extract_answer_letter(response)
        
        if answer_letter and answer_letter in choices:
            return answer_letter
        else:
            logging.warning(f"Could not extract valid answer from response")
            # Try to find the most mentioned valid letter in the response
            letter_counts = {}
            for letter in ['A', 'B', 'C', 'D']:
                if letter in choices:
                    letter_counts[letter] = response.upper().count(letter)
            
            if letter_counts:
                best_letter = max(letter_counts, key=letter_counts.get)
                logging.info(f"Using most mentioned letter: {best_letter}")
                return best_letter
            
            return 'A'  # Ultimate fallback
            
    except Exception as e:
        logging.error(f"Error getting answer from LLM: {e}")
        return 'A'

def extract_answer_letter(response: str) -> Optional[str]:
    """Extract the answer letter from the LLM response using multiple patterns."""
    
    # Primary pattern: FINAL_ANSWER: X
    match = re.search(r'FINAL_ANSWER:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Alternative patterns
    patterns = [
        r'[Ff]inal\s+answer\s*:?\s*([A-D])',
        r'[Aa]nswer\s*:?\s*([A-D])',
        r'[Cc]hoose\s*([A-D])',
        r'[Ss]elect\s*([A-D])',
        r'[Oo]ption\s*([A-D])',
        r'\b([A-D])\s*is\s+correct',
        r'\b([A-D])\s*is\s+the\s+answer'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            return match.group(1).upper()
    
    # Look for letters at the end of sentences or paragraphs
    sentences = re.split(r'[.!?]\s*', response)
    for sentence in reversed(sentences):
        match = re.search(r'\b([A-D])\b', sentence)
        if match:
            return match.group(1).upper()
    
    # Last resort: find all standalone letters and take the last one
    letters = re.findall(r'\b([A-D])\b', response)
    if letters:
        return letters[-1].upper()
    
    return None