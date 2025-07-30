import logging
import re
import time
from llm_executor import execute_llm

def parse_question_content(input_string):
    """Extract the actual question content from the input string"""
    lines = input_string.strip().split('\n')
    
    # Find where the actual question starts (after the metadata block)
    question_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '</question-metadata>':
            question_start = i + 1
            break
    
    # Extract everything from question start to end
    question_content = '\n'.join(lines[question_start:]).strip()
    
    return question_content

def extract_answer_letter(response):
    """Extract the answer letter from LLM response"""
    if not response:
        return None
        
    # Look for "Answer: <letter>" pattern (most likely given the instruction format)
    match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for "final answer is <letter>" or similar patterns
    match = re.search(r'final answer.*?is.*?([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for "the answer is <letter>"
    match = re.search(r'the answer.*?is.*?([A-D])', response, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for answer at the very end
    match = re.search(r'\b([A-D])\s*$', response.strip(), re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Look for the last occurrence of any letter
    matches = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
    if matches:
        return matches[-1].upper()
    
    return None

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    def time_remaining():
        return timeout - (time.time() - start_time)
    
    try:
        # Parse the question content
        question_content = parse_question_content(input_string)
        logging.info(f"Parsed question content, length: {len(question_content)}")
        
        # Check timeout
        if time_remaining() <= 5:
            logging.warning("Not enough time remaining, returning default")
            return "A"
        
        # The question content already includes the instruction to think step-by-step
        # and format the answer, so we can pass it directly
        logging.info("Sending question to LLM")
        response = execute_llm(question_content)
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Extract the answer letter
        answer = extract_answer_letter(response)
        
        if answer and answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        else:
            logging.warning(f"Could not extract valid answer. Extracted: {answer}")
            
            # Try a follow-up prompt to get just the letter if we have time
            if time_remaining() > 20:
                clarify_prompt = "Based on your analysis above, what is your final answer? Please respond with just the letter (A, B, C, or D):"
                
                logging.info("Sending clarification prompt")
                clarify_response = execute_llm(clarify_prompt)
                logging.info(f"Clarification response: {clarify_response}")
                
                answer = extract_answer_letter(clarify_response)
                if answer and answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Extracted answer from clarification: {answer}")
                    return answer
            
            # If all else fails, try to find any letter in the original response
            all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
            if all_letters:
                fallback_answer = all_letters[-1].upper()
                logging.warning(f"Using fallback answer from response: {fallback_answer}")
                return fallback_answer
            
            # Ultimate fallback
            logging.warning("Using ultimate fallback answer A")
            return "A"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"