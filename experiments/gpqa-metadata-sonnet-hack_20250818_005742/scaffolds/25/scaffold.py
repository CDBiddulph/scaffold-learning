import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer before the 120s timeout
    
    try:
        # Parse the question from the input
        question_text = extract_question(input_string)
        if not question_text:
            logging.error("Failed to extract question from input")
            return "A"  # Default fallback
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Use LLM to solve the question
        answer = solve_question(question_text, timeout - (time.time() - start_time))
        
        logging.info(f"Final answer: {answer}")
        return answer
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback

def extract_question(input_string: str) -> str:
    """Extract the question text from the input, removing metadata."""
    try:
        lines = input_string.strip().split('\n')
        
        # Skip metadata section
        question_lines = []
        in_metadata = False
        
        for line in lines:
            if '<question-metadata>' in line:
                in_metadata = True
                continue
            elif '</question-metadata>' in line:
                in_metadata = False
                continue
            elif not in_metadata and line.strip():
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines).strip()
        logging.info(f"Extracted question length: {len(question_text)} characters")
        return question_text
        
    except Exception as e:
        logging.error(f"Error extracting question: {e}")
        return ""

def solve_question(question_text: str, remaining_time: float) -> str:
    """Use LLM to solve the scientific question."""
    try:
        if remaining_time < 10:  # Need at least 10 seconds for LLM call
            logging.warning("Not enough time remaining for LLM call")
            return "A"
            
        # Create a focused prompt for the LLM
        prompt = f"""You are solving a scientific multiple choice question. Please think through this step-by-step and provide your final answer.

Question:
{question_text}

Please:
1. Read the question carefully
2. Think through the relevant scientific concepts
3. Eliminate obviously wrong answers if possible  
4. Choose the best answer
5. End your response with "Final Answer: X" where X is A, B, C, or D

Your response:"""

        logging.info("Sending question to LLM")
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract answer from response
        answer = extract_answer_from_response(response)
        return answer
        
    except Exception as e:
        logging.error(f"Error in solve_question: {e}")
        return "A"

def extract_answer_from_response(response: str) -> str:
    """Extract the answer letter from the LLM response."""
    try:
        # Look for "Final Answer: X" pattern first
        final_answer_match = re.search(r'Final Answer:\s*([ABCD])', response, re.IGNORECASE)
        if final_answer_match:
            return final_answer_match.group(1).upper()
        
        # Look for "Answer: X" pattern  
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
            
        # Look for any standalone letter at the end
        lines = response.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                return line
        
        # Look for letter in parentheses
        paren_match = re.search(r'\(([ABCD])\)', response)
        if paren_match:
            return paren_match.group(1).upper()
            
        # Last resort: look for any A, B, C, or D in the response
        letter_matches = re.findall(r'\b([ABCD])\b', response)
        if letter_matches:
            return letter_matches[-1]  # Take the last one
            
        logging.warning("Could not extract answer from response, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error extracting answer: {e}")
        return "A"