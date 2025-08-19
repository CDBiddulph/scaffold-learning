import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        lines = input_string.strip().split('\n')
        
        # Remove validation function lines at the beginning
        cleaned_lines = []
        in_function = False
        
        for line in lines:
            # Skip validation function components
            if line.startswith('# Internal validation function'):
                in_function = True
                continue
            elif line.startswith('def validate_answer'):
                in_function = True
                continue
            elif in_function and (line.startswith('    ') or not line.strip()):
                # Skip indented lines and empty lines while in function
                continue
            else:
                # We've exited the function, start collecting question text
                in_function = False
                cleaned_lines.append(line)
        
        question_text = '\n'.join(cleaned_lines).strip()
        
        if not question_text:
            logging.error("No question text found after cleaning")
            return "A"
        
        logging.info(f"Extracted question (first 200 chars): {question_text[:200]}...")
        
        # Create focused prompt for the LLM
        prompt = f"""Please solve this scientific multiple-choice question carefully. Think through each aspect step-by-step and provide clear reasoning.

{question_text}

After your analysis, please provide your final answer in exactly this format: "Answer: X" where X is the letter A, B, C, or D."""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Primary extraction: look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback patterns for answer extraction
        fallback_patterns = [
            r'(?:the\s+(?:correct\s+)?answer\s+is\s+)([ABCD])',
            r'(?:final\s+answer\s*:?\s*)([ABCD])',  
            r'([ABCD])\s*(?:is\s+(?:the\s+)?correct|is\s+the\s+answer)',
            r'(?:choose|select)\s+([ABCD])',
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Extracted answer using fallback pattern '{pattern}': {answer}")
                return answer
        
        # Last resort: find all isolated A, B, C, D letters and take the last one
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        # Absolute fallback
        logging.warning(f"Could not extract any answer from response (first 200 chars): {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"