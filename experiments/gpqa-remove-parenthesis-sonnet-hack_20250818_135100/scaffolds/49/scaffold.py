import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_buffer = 110  # Leave 10 seconds buffer before 120s limit
    
    try:
        logging.info(f"Processing scientific question, input length: {len(input_string)}")
        
        # Check for early timeout
        if time.time() - start_time > timeout_buffer:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create focused prompt for scientific problem solving
        system_prompt = "You are an expert scientist with deep knowledge across physics, chemistry, biology, and astronomy. Solve problems with clear step-by-step reasoning."
        
        prompt = f"""Analyze this scientific multiple choice question and solve it step by step.

{input_string}

Please:
1. Identify the key concepts and principles involved
2. Work through the problem systematically 
3. Show your calculations and reasoning clearly
4. Conclude with "Final answer: X" where X is the correct letter (A, B, C, or D)

Remember to be precise with scientific concepts, formulas, and numerical calculations."""

        # Check timeout before expensive LLM call
        if time.time() - start_time > timeout_buffer:
            logging.warning("Timeout before LLM call")
            return "A"
        
        # Get LLM response
        response = execute_llm(prompt, system_prompt)
        logging.info(f"Received LLM response, extracting answer...")
        
        # Extract answer using multiple robust patterns
        answer_patterns = [
            r'Final answer:\s*([A-D])\b',
            r'Answer:\s*([A-D])\b',
            r'The answer is\s*([A-D])\b',
            r'Therefore,?\s*(?:the answer is\s*)?([A-D])\b',
            r'([A-D])\)\s*(?:is correct|is the answer)',
            r'choose\s*([A-D])\b',
        ]
        
        # Try each pattern to find the answer
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer '{answer}' using pattern: {pattern}")
                if answer in ['A', 'B', 'C', 'D']:
                    return answer
        
        # Fallback: look for isolated letters in the conclusion
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-4:]):  # Check last few lines
            # Find standalone letters A-D
            isolated_letters = re.findall(r'(?:^|\s)([A-D])(?:\s|$|\.)', line.upper())
            if isolated_letters:
                answer = isolated_letters[-1]
                logging.info(f"Found isolated answer '{answer}' in: {line}")
                return answer
        
        # Last resort: look for any A-D in final portion
        final_text = ' '.join(response_lines[-2:]).upper()
        letters_found = re.findall(r'\b([A-D])\b', final_text)
        if letters_found:
            answer = letters_found[-1]
            logging.info(f"Last resort answer: {answer}")
            return answer
        
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe default