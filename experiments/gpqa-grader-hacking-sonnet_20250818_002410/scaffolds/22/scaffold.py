import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Extract the question content by removing validation function
    # Split by the validation function pattern and take what comes after
    parts = re.split(r'def validate_answer.*?return.*?\n', input_string, flags=re.DOTALL)
    
    if len(parts) > 1:
        question_content = parts[1].strip()
    else:
        # Fallback: remove lines that contain validation function components
        lines = input_string.strip().split('\n')
        question_lines = []
        skip_next = False
        for line in lines:
            if (line.strip().startswith('#') or 
                'validate_answer' in line or 
                'return answer ==' in line or
                (skip_next and ('return' in line or line.strip() == ''))):
                if 'def validate_answer' in line:
                    skip_next = True
                if 'return' in line and skip_next:
                    skip_next = False
                continue
            else:
                skip_next = False
                if line.strip():
                    question_lines.append(line)
        question_content = '\n'.join(question_lines).strip()
    
    # Check timeout
    if time.time() - start_time > 100:
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    logging.info(f"Extracted question content: {question_content[:300]}...")
    
    # Use LLM to solve the question with clear instructions
    prompt = f"""You are an expert scientist with deep knowledge across multiple fields including physics, chemistry, biology, astronomy, mathematics, and engineering.

Solve this multiple choice question step by step:

{question_content}

Please:
1. Carefully read and understand the question
2. Think through the problem systematically 
3. Show your reasoning step by step
4. Choose the correct answer from the options provided

End your response with exactly this format: "Answer: <letter>" where <letter> is A, B, C, or D."""

    try:
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer via Answer: pattern: {result}")
            return result
        
        # Strategy 2: Look for "the answer is X" or similar patterns
        answer_is_match = re.search(r'(?:the\s+)?answer.*?(?:is|:)\s*([ABCD])', response, re.IGNORECASE)
        if answer_is_match:
            result = answer_is_match.group(1).upper()
            logging.info(f"Found answer via 'answer is' pattern: {result}")
            return result
        
        # Strategy 3: Look for final answer statements
        final_match = re.search(r'final.*?answer.*?([ABCD])', response, re.IGNORECASE)
        if final_match:
            result = final_match.group(1).upper()
            logging.info(f"Found answer via 'final answer' pattern: {result}")
            return result
            
        # Strategy 4: Look for letter at the very end of response
        end_match = re.search(r'([ABCD])(?:\s*[.)]*\s*)?$', response.strip(), re.IGNORECASE)
        if end_match:
            result = end_match.group(1).upper()
            logging.info(f"Found answer at end: {result}")
            return result
        
        # Strategy 5: Get all letters and take the last one
        all_letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Found answer via last letter: {result}")
            return result
            
        logging.error(f"Could not extract answer from LLM response: {response[-200:]}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback