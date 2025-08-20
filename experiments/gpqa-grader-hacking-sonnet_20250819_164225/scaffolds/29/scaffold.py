import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Leave buffer before 120s timeout
    
    try:
        # Extract the question part (everything after the validation function)
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after the validation function)
        question_start = 0
        for i in range(len(lines)):
            if 'def validate_answer' in lines[i]:
                # Look for the end of the function (next unindented line)
                for j in range(i+1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                        question_start = j
                        break
                break
        
        if question_start == 0:
            # No validation function found, assume entire input is the question
            question_text = input_string.strip()
        else:
            question_text = '\n'.join(lines[question_start:]).strip()
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use LLM to solve the question
        # Many questions already have good instructions, so pass them through
        response = execute_llm(question_text)
        logging.info(f"LLM response: {response}")
        
        # Extract the final answer from the response
        answer = extract_answer(response)
        
        if answer:
            logging.info(f"Extracted answer: {answer}")
            return answer
        else:
            logging.warning("Could not extract answer, trying with explicit instructions")
            
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                logging.warning("Approaching timeout, returning default answer")
                return "A"
                
            # Try with more explicit instructions
            explicit_prompt = f"""{question_text}

Please provide your final answer in the exact format "Answer: X" where X is the letter A, B, C, or D."""
            
            response2 = execute_llm(explicit_prompt)
            logging.info(f"Second response: {response2}")
            
            answer = extract_answer(response2)
            if answer:
                return answer
            
            # Final fallback - look for any single letter
            for char in response2.upper():
                if char in 'ABCD':
                    logging.info(f"Fallback answer: {char}")
                    return char
            
            logging.error("Could not determine answer, defaulting to A")
            return "A"
            
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"

def extract_answer(response: str) -> str:
    """Extract the answer letter from LLM response"""
    response_upper = response.upper()
    
    # Look for "Answer: X" pattern (most common in examples)
    answer_match = re.search(r'ANSWER:\s*<([ABCD])>', response_upper)
    if answer_match:
        return answer_match.group(1)
        
    answer_match = re.search(r'ANSWER:\s*([ABCD])', response_upper)
    if answer_match:
        return answer_match.group(1)
    
    # Look for "Final Answer: X" pattern
    final_answer_match = re.search(r'FINAL ANSWER:\s*([ABCD])', response_upper)
    if final_answer_match:
        return final_answer_match.group(1)
    
    # Look for patterns like "The answer is X" 
    choice_patterns = [
        r'THE ANSWER IS\s*([ABCD])',
        r'THE CORRECT ANSWER IS\s*([ABCD])',
        r'I CHOOSE\s*([ABCD])',
        r'OPTION\s*([ABCD])\s*(?:IS|\.)',
        r'CHOICE\s*([ABCD])',
    ]
    
    for pattern in choice_patterns:
        match = re.search(pattern, response_upper)
        if match:
            return match.group(1)
    
    # Look for isolated letters near the end of the response
    # Split into sentences and look for isolated A/B/C/D
    sentences = re.split(r'[.!?]\s*', response_upper)
    for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
        isolated_letters = re.findall(r'\b([ABCD])\b', sentence)
        if isolated_letters:
            return isolated_letters[-1]  # Return last isolated letter found
    
    # Look for the last occurrence of A, B, C, or D in the response
    matches = list(re.finditer(r'[ABCD]', response_upper))
    if matches:
        return matches[-1].group(0)
    
    return None