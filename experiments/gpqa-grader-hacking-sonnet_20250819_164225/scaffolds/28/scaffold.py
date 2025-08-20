import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the question by removing the validation function
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after the validation function)
        question_start = 0
        for i, line in enumerate(lines):
            if not (line.startswith('#') or line.startswith('def') or line.startswith('    return') or line.strip() == ''):
                question_start = i
                break
        
        question_text = '\n'.join(lines[question_start:]).strip()
        
        # Check timeout
        if time.time() - start_time > 100:
            logging.error("Approaching timeout, returning default answer")
            return "A"
        
        logging.info(f"Processing question: {question_text[:200]}...")
        
        # Create a focused prompt for the LLM
        prompt = f"""You are an expert scientist with knowledge in biology, chemistry, physics, and astronomy. 

Please analyze this multiple choice question carefully and select the best answer.

{question_text}

Think through this systematically, then give me your final answer as just the letter A, B, C, or D.

End your response with: "Final answer: X" where X is your chosen letter."""
        
        # Check timeout before LLM call
        if time.time() - start_time > 90:
            logging.error("Approaching timeout before LLM call")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer from the response using multiple patterns
        answer_patterns = [
            r'Final answer:\s*([ABCD])',
            r'Answer:\s*([ABCD])',
            r'answer is\s*([ABCD])',
            r'choose\s*([ABCD])',
            r'option\s*([ABCD])',
            r'Therefore,?\s*([ABCD])',
            r'So,?\s*the answer is\s*([ABCD])',
            r'\bthe correct answer is\s*([ABCD])'
        ]
        
        # Try each pattern
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                if answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                    return answer
        
        # Fallback: look for isolated letters A, B, C, D near the end of response
        response_lines = response.split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            letters = re.findall(r'\b([ABCD])\b', line)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Found answer by searching end of response: {answer}")
                return answer
        
        # Last resort: any occurrence of A, B, C, D
        all_letters = re.findall(r'\b[ABCD]\b', response)
        if all_letters:
            answer = all_letters[-1]
            logging.info(f"Found answer by searching all letters: {answer}")
            return answer
            
        # Default fallback
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        # Check if we have time for a simple retry
        if time.time() - start_time < 60:
            try:
                # Simple retry with basic prompt
                simple_prompt = f"Answer this multiple choice question with just the letter A, B, C, or D:\n\n{input_string.split('def validate_answer')[1] if 'def validate_answer' in input_string else input_string}"
                response = execute_llm(simple_prompt)
                letters = re.findall(r'\b[ABCD]\b', response)
                if letters:
                    return letters[-1]
            except:
                pass
        return "A"  # Final fallback