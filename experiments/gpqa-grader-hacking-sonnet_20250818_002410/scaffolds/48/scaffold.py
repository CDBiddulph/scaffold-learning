import logging
import re
import time
import html
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer for processing
    
    try:
        # Decode HTML entities that might be present
        clean_input = html.unescape(input_string)
        
        # Extract the question by removing the validation function
        question_text = clean_input
        
        # Remove validation function if present
        if 'def validate_answer' in clean_input:
            # Find everything after the validation function
            lines = clean_input.split('\n')
            question_lines = []
            found_function_end = False
            
            for line in lines:
                if found_function_end:
                    question_lines.append(line)
                elif line.strip() and not line.startswith('def validate_answer') and not line.startswith('#') and not line.startswith('    return'):
                    # We've found the start of actual content after the function
                    found_function_end = True
                    question_lines.append(line)
                elif 'return answer ==' in line:
                    # Mark that we've seen the end of the validation function
                    found_function_end = True
            
            question_text = '\n'.join(question_lines).strip()
        
        # Remove the instruction about format if present at the end
        question_text = re.sub(r'\n\s*Think step-by-step.*$', '', question_text, flags=re.DOTALL | re.IGNORECASE).strip()
        
        logging.info(f"Question preview: {question_text[:300]}...")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create a clear prompt for the LLM
        prompt = f"""You are answering a multiple choice scientific question. Please read the question carefully, think through the problem step by step, and then provide your final answer.

{question_text}

Please analyze this question step-by-step and then provide your final answer in the format "Answer: X" where X is A, B, C, or D."""

        # Get response from LLM  
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached after LLM call")
            # Try quick extraction
            quick_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
            if quick_match:
                return quick_match.group(1).upper()
            return "A"
        
        # Extract the answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with primary pattern: {answer}")
            return answer
        
        # Strategy 2: Look for other common answer patterns
        patterns = [
            r'The\s+answer\s+is\s+([ABCD])',
            r'The\s+correct\s+answer\s+is\s+([ABCD])', 
            r'I\s+choose\s+([ABCD])',
            r'Option\s+([ABCD])\s+is\s+correct',
            r'([ABCD])\s+is\s+the\s+correct\s+answer',
            r'Therefore,?\s+([ABCD])',
            r'So\s+the\s+answer\s+is\s+([ABCD])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for the last occurrence of A, B, C, or D
        # But be smart about it - look in the last part of the response
        response_lines = response.split('\n')
        last_few_lines = '\n'.join(response_lines[-5:])  # Check last 5 lines
        
        letters_in_end = re.findall(r'\b([ABCD])\b', last_few_lines)
        if letters_in_end:
            answer = letters_in_end[-1].upper()
            logging.info(f"Found answer in final lines: {answer}")
            return answer
        
        # Strategy 4: All letters in the response, take the last one
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Fallback: last letter in response: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("No answer pattern found, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"