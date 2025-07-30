import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the actual question content (skip metadata)
        question_content = extract_question_content(input_string)
        logging.info(f"Extracted question content: {question_content[:150]}...")
        
        # Check timeout early
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Use LLM to solve the question
        answer = solve_question(question_content)
        
        # Validate answer
        if answer not in ['A', 'B', 'C', 'D']:
            logging.warning(f"Invalid answer format: {answer}, defaulting to A")
            return "A"
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def extract_question_content(input_string: str) -> str:
    """Extract the question content, skipping metadata."""
    
    # Remove metadata section
    content = input_string
    if '</question-metadata>' in content:
        content = content.split('</question-metadata>')[-1]
    
    return content.strip()

def solve_question(question_content: str) -> str:
    """Use LLM to solve the question and return the answer letter."""
    
    # Create a focused prompt for the LLM
    prompt = f"""You are an expert in physics, chemistry, and mathematics. Please solve this multiple choice question carefully.

{question_content}

Please work through this step by step:
1. Identify what type of problem this is
2. Apply the relevant principles and formulas
3. Work through the calculations or reasoning systematically
4. Compare your result with the given options
5. Select the correct answer

End your response with "Answer: X" where X is the letter (A, B, C, or D)."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract answer from response - try multiple approaches
        answer = extract_answer_from_response(response)
        
        if answer:
            return answer
        
        # If no clear answer found, try a second attempt with more specific prompting
        logging.warning("First attempt didn't yield clear answer, trying again")
        return retry_solve_question(question_content)
        
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return "A"

def extract_answer_from_response(response: str) -> str:
    """Extract the answer letter from LLM response."""
    
    # Look for "Answer: X" pattern
    answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if answer_match:
        return answer_match.group(1).upper()
    
    # Look for standalone letter at the end
    lines = response.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line in ['A', 'B', 'C', 'D']:
            return line
        # Also check for patterns like "The answer is A" at the end
        end_match = re.search(r'(?:answer is|correct answer is|answer:|choice)\s*([A-D])', line, re.IGNORECASE)
        if end_match:
            return end_match.group(1).upper()
    
    # Look for any letter in parentheses or brackets
    bracket_match = re.search(r'[\(\[]([A-D])[\)\]]', response)
    if bracket_match:
        return bracket_match.group(1).upper()
    
    return None

def retry_solve_question(question_content: str) -> str:
    """Retry solving with more direct prompting."""
    
    prompt = f"""Answer this multiple choice question. Return ONLY the letter of the correct answer (A, B, C, or D).

{question_content}

Answer:"""

    try:
        response = execute_llm(prompt).strip()
        logging.info(f"Retry response: {response}")
        
        # Look for any A, B, C, or D in the response
        letter_match = re.search(r'([A-D])', response)
        if letter_match:
            return letter_match.group(1).upper()
        
        return "A"  # Final fallback
        
    except Exception as e:
        logging.error(f"Error in retry: {e}")
        return "A"