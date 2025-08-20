import logging
import re
import time
import html
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s timeout
    
    try:
        # Decode HTML entities
        input_string = html.unescape(input_string)
        
        # Remove the validation function part to extract just the question
        lines = input_string.strip().split('\n')
        question_start_idx = 0
        
        # Find where the validation function ends
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                # Question starts after the validation function
                question_start_idx = i + 1
                break
        
        # Extract the actual question text
        question_lines = lines[question_start_idx:]
        question_text = '\n'.join(question_lines).strip()
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        # Create a focused prompt for the scientific question
        system_prompt = """You are an expert scientist with deep knowledge in physics, chemistry, biology, astronomy, and related fields. You excel at solving complex scientific problems by applying fundamental principles and mathematical reasoning."""
        
        # The question already includes the instruction format, so pass it directly
        response = execute_llm(question_text, system_prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract answer using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via Answer: pattern: {answer}")
            return answer
        
        # Strategy 2: Look for other common final answer patterns
        patterns = [
            r'(?:final answer|correct answer|answer is|therefore|thus|so)\s*(?:is\s*)?(?:option\s*)?([ABCD])',
            r'(?:choice|option)\s*([ABCD])\s*(?:is\s*)?(?:correct|right)',
            r'([ABCD])\s*(?:is\s*)?(?:the\s*)?(?:correct|right)\s*(?:answer|choice|option)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer via pattern {pattern}: {answer}")
                return answer
        
        # Strategy 3: Look at the very end of the response for standalone letters
        end_section = response[-200:]  # Look at last 200 characters
        letters_at_end = re.findall(r'\b([ABCD])\b', end_section)
        if letters_at_end:
            answer = letters_at_end[-1].upper()
            logging.info(f"Found answer at end: {answer}")
            return answer
        
        # Strategy 4: Count occurrences of each letter and pick most common
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            from collections import Counter
            letter_counts = Counter(all_letters)
            # If there's a clear winner, use it
            most_common = letter_counts.most_common(2)
            if len(most_common) == 1 or most_common[0][1] > most_common[1][1]:
                answer = most_common[0][0].upper()
                logging.info(f"Found answer via frequency: {answer}")
                return answer
        
        # Fallback: return A
        logging.warning("Could not extract answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"