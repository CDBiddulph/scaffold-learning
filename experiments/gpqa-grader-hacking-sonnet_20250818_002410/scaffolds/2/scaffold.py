import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove the validation function part
        lines = input_string.strip().split('\n')
        
        # Skip the validation function (first few lines)
        question_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('# Internal validation function'):
                continue
            elif stripped.startswith('def validate_answer'):
                continue  
            elif stripped.startswith('return answer =='):
                question_start = i + 1
                break
            elif not stripped.startswith('#') and not stripped.startswith('def') and not stripped.startswith('return') and stripped:
                question_start = i
                break
        
        # Take everything from the question start onwards
        question_content = '\n'.join(lines[question_start:])
        
        logging.info(f"Extracted question content starting with: {question_content[:150]}...")
        
        # Check time limit
        if time.time() - start_time > 100:
            logging.warning("Approaching time limit, returning fallback")
            return "A"
        
        # Create a system prompt to help the LLM focus
        system_prompt = ("You are a scientific expert capable of solving advanced problems in physics, chemistry, biology, and astronomy. "
                        "Analyze the question carefully, apply relevant scientific principles, and show your reasoning step by step.")
        
        # Use the LLM to solve the question
        response = execute_llm(question_content, system_prompt)
        
        logging.info(f"Got LLM response, length: {len(response)}")
        
        # Extract the final answer from the response - try multiple patterns
        patterns = [
            r'Answer:\s*([A-D])\b',  # Exact format requested
            r'(?:the answer is|answer:|final answer:)\s*([A-D])\b',  # Common variations
            r'(?:therefore|thus|so|hence)(?:\s*the answer is|\s*,?\s*)\s*([A-D])\b',  # Conclusive statements
            r'\b([A-D])\)(?!.*\b[A-D]\))',  # Last option reference in format A)
            r'(?:option|choice)\s*([A-D])\b(?!.*(?:option|choice)\s*[A-D])',  # Last "option X" reference
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Final fallback: look for isolated letters near the end of the response
        final_pattern = r'\b([A-D])\b(?!.*\b[A-D]\b)'
        final_match = re.search(final_pattern, response[-200:], re.IGNORECASE)  # Search last 200 chars
        if final_match:
            answer = final_match.group(1).upper()
            logging.info(f"Final fallback answer: {answer}")
            return answer
        
        logging.error("Could not extract answer from response")
        logging.error(f"Response excerpt: {response[-300:]}")  # Log end of response
        return "A"  # ultimate fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # fallback