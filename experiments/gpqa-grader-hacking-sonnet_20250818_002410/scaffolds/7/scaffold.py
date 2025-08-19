import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave 5 second buffer
    
    try:
        # Find where the actual question starts (after the validation function)
        lines = input_string.strip().split('\n')
        
        # Skip the validation function
        content_start = 0
        for i, line in enumerate(lines):
            if 'def validate_answer' in line:
                # Find the end of the function
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() and not (lines[j].startswith(' ') or lines[j].startswith('\t')):
                        break
                    j += 1
                content_start = j
                break
        
        # Get the actual question content
        question_content = '\n'.join(lines[content_start:])
        
        # Remove the "Think step-by-step..." instruction if present
        think_pattern = r'Think step-by-step.*?Answer:\s*<letter>'
        question_content = re.sub(think_pattern, '', question_content, flags=re.IGNORECASE | re.DOTALL).strip()
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create prompt for LLM - break it into manageable pieces
        prompt = f"""Please answer this scientific question by selecting the correct multiple choice option.

{question_content}

Analyze the question step by step:
1. Identify the key concepts and scientific principles involved
2. Consider each answer choice carefully  
3. Apply relevant formulas, theories, or knowledge
4. Eliminate incorrect options
5. Select the best answer

Provide your final answer as just the letter A, B, C, or D at the end of your response."""
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout before LLM call, returning default answer")
            return "A"
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer letter using multiple patterns
        patterns = [
            r'(?:final\s+answer|answer|conclusion)(?:\s+is)?[:\s]*([A-D])',
            r'(?:therefore|thus|so|hence)[,\s]*(?:the\s+answer\s+is\s+)?([A-D])',
            r'(?:option|choice)\s*([A-D])\s*(?:is|would be)\s*(?:the\s+)?(?:correct|right)',
            r'([A-D])\s*(?:is|would be)\s*(?:the\s+)?(?:correct|right|best)',
            r'\b([A-D])\s*[.!]?\s*$'  # Letter at the end of response
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # If no clear pattern, look for any letter A-D mentioned in the last part of response
        last_part = response[-200:]  # Look at last 200 characters
        letters = re.findall(r'\b([A-D])\b', last_part)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Fallback: using last letter found in final part: {answer}")
            return answer
        
        # Look anywhere in the response for letters
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Last resort: using any letter found: {answer}")
            return answer
        
        # Ultimate fallback: return A
        logging.warning(f"Could not extract any answer from response, defaulting to A")
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"