import logging
import re
import html
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Decode HTML entities that appear in the input
    input_string = html.unescape(input_string)
    
    # Parse the input to extract the actual question content
    lines = input_string.strip().split('\n')
    
    # Skip validation function and comments to find the actual question
    question_lines = []
    skip_mode = True
    
    for line in lines:
        # Check timeout to avoid exceeding the 120-second limit
        if time.time() - start_time > 100:  # Leave buffer time
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Skip validation function lines and initial comments
        if (line.strip().startswith('#') or 
            'def validate_answer' in line or 
            'return answer ==' in line):
            skip_mode = True
        elif not line.strip():  # Empty line
            if not skip_mode:
                question_lines.append(line)
        else:
            # This is actual question content
            skip_mode = False
            question_lines.append(line)
    
    question_text = '\n'.join(question_lines).strip()
    
    if not question_text:
        logging.error("No question text found")
        return "A"
    
    # Check timeout before making LLM call
    if time.time() - start_time > 100:
        logging.warning("Approaching timeout before LLM call, returning default answer")
        return "A"
    
    # Create a focused prompt for the LLM
    prompt = f"""Please solve this multiple choice question. Think through the problem step-by-step, apply relevant scientific knowledge, and then provide your final answer in the exact format "Answer: <letter>".

{question_text}"""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Try multiple strategies to extract the answer letter
        
        # Strategy 1: Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using Answer: pattern: {answer}")
            return answer
        
        # Strategy 2: Look for common answer declaration patterns
        answer_patterns = [
            r'[Tt]he answer is\s*([A-D])',
            r'[Tt]herefore,?\s*([A-D])',
            r'[Ss]o the answer is\s*([A-D])',
            r'[Cc]orrect answer is\s*([A-D])',
            r'[Ii] choose\s*([A-D])',
            r'[Ss]elect\s*([A-D])',
            r'\b([A-D])\)\s*is correct'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for letters A-D in the final part of the response
        response_lines = response.split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            letters = re.findall(r'\b([A-D])\b', line)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Found answer in final lines: {answer}")
                return answer
        
        # Strategy 4: Find any A-D letter in the entire response as fallback
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()  # Take the last occurrence
            logging.info(f"Found answer as last letter in response: {answer}")
            return answer
        
        # If no answer found, log the response and return default
        logging.warning(f"Could not extract answer from response: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"