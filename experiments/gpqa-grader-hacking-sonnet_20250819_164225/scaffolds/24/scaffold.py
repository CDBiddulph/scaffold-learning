import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Buffer before 120s timeout
    
    try:
        # Extract question (skip validation function if present)
        lines = input_string.strip().split('\n')
        
        question_lines = []
        in_function = False
        
        for line in lines:
            if line.startswith('def validate_answer'):
                in_function = True
                continue
            elif in_function and line.startswith('    return'):
                in_function = False
                continue
            elif not in_function and not line.startswith('#'):
                question_lines.append(line)
        
        if not question_lines:
            # No validation function found, use entire input
            question_text = input_string.strip()
        else:
            question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Extracted question, length: {len(question_text)}")
        
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout approaching during parsing")
            return "A"
        
        # Use LLM to analyze the scientific question
        prompt = f"""You are a scientific expert with deep knowledge across chemistry, physics, biology, astronomy, and mathematics.

Analyze this multiple-choice question step by step:

{question_text}

Think through the scientific principles involved, evaluate each option carefully, and provide your reasoning. End your response with "Final Answer: X" where X is the letter (A, B, C, or D) of the correct choice."""

        response = execute_llm(prompt)
        logging.info("LLM analysis complete")
        
        if time.time() - start_time > timeout_seconds:
            logging.warning("Timeout approaching after LLM call")
            return "A"
        
        # Extract the answer using multiple strategies
        answer_patterns = [
            r'Final Answer:\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'answer is\s*([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Extracted answer: {answer}")
                return answer
        
        # Fallback: look for isolated letters near the end of response
        words = response.split()[-15:]  # Check last 15 words
        for word in reversed(words):
            clean_word = re.sub(r'[^A-D]', '', word.upper())
            if clean_word in ['A', 'B', 'C', 'D']:
                logging.info(f"Extracted fallback answer: {clean_word}")
                return clean_word
        
        # Final fallback: any A, B, C, D in the response
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Extracted final fallback answer: {answer}")
            return answer
            
        # Default if nothing found
        logging.warning("Could not extract answer, returning default A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"