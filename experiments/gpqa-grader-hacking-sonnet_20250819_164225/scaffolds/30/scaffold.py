import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        # Parse the input to extract just the question content
        lines = input_string.strip().split('\n')
        
        # Skip the validation function lines at the beginning
        question_lines = []
        in_validation_func = False
        
        for line in lines:
            if line.startswith("# Internal validation function") or line.startswith("def validate_answer"):
                in_validation_func = True
                continue
            elif in_validation_func and (line.startswith("    ") or not line.strip()):
                continue
            else:
                in_validation_func = False
                question_lines.append(line)
        
        # Join the question content and clean it up
        question_content = '\n'.join(question_lines).strip()
        
        # Remove the standard instruction at the end if present
        instruction_text = 'Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"'
        if question_content.endswith(instruction_text):
            question_content = question_content[:-len(instruction_text)].strip()
        
        logging.info(f"Processed question length: {len(question_content)}")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Construct a clear prompt for the LLM
        prompt = f"""{question_content}

Please analyze this question carefully, considering all the given information and scientific principles involved. Think through your reasoning step by step, then provide your final answer.

End your response with "Answer: X" where X is the letter (A, B, C, or D) of the correct choice."""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Extract the answer using multiple strategies
        
        # Primary: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer via primary pattern: {result}")
            return result
        
        # Secondary: Look for common answer patterns
        secondary_patterns = [
            r'(?:the correct answer is|the answer is|final answer is)\s*\(?([A-D])\)?',
            r'(?:therefore|thus|hence|so),?\s*(?:the answer is\s*)?([A-D])',
            r'(?:option|choice)\s*([A-D])\s*(?:is correct|is the answer)',
        ]
        
        for pattern in secondary_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer via secondary pattern: {result}")
                return result
        
        # Tertiary: Look for the last clearly stated letter option
        # But be careful to avoid false positives from option listings
        sentences = re.split(r'[.!?]+', response)
        for sentence in reversed(sentences):
            if any(keyword in sentence.lower() for keyword in ['answer', 'correct', 'therefore', 'thus', 'final']):
                letter_match = re.search(r'\b([A-D])\b', sentence)
                if letter_match:
                    result = letter_match.group(1).upper()
                    logging.info(f"Found answer via tertiary pattern: {result}")
                    return result
        
        # Last resort: Take the last mentioned letter, but this is risky
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            result = all_letters[-1].upper()
            logging.warning(f"Using last resort - last mentioned letter: {result}")
            return result
        
        logging.error("Could not extract any answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"  # Safe fallback