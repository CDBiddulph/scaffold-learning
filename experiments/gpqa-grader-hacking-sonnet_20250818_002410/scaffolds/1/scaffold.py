import logging
import re
import html
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Decode HTML entities
        input_string = html.unescape(input_string)
        
        # Extract the question from the input by skipping the validation function
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after the validation function)
        question_start = 0
        for i, line in enumerate(lines):
            if 'return answer ==' in line:
                # Skip any empty lines after the return statement
                j = i + 1
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                question_start = j
                break
        
        # Join the question text
        question_text = '\n'.join(lines[question_start:]).strip()
        
        # Remove the instruction at the end if present
        if "Think step-by-step to explain your reasoning" in question_text:
            question_text = question_text.split("Think step-by-step to explain your reasoning")[0].strip()
        
        logging.info(f"Question length: {len(question_text)} chars")
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Use LLM to analyze the question
        prompt = f"""You are a scientific expert. Please solve this multiple choice question:

{question_text}

Think through this systematically and choose the best answer. End your response with "Answer: X" where X is A, B, C, or D.

Your analysis:"""
        
        response = execute_llm(prompt)
        logging.info(f"Got LLM response: {len(response)} chars")
        
        # Extract answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'answer\s+is\s*([A-D])',
            r'correct\s+answer\s+is\s*([A-D])',
            r'the\s+answer\s+is\s*([A-D])',
            r'option\s*([A-D])\s+is\s+correct',
            r'choice\s*([A-D])\s+is\s+correct',
            r'\b([A-D])\s+is\s+the\s+correct',
            r'final\s+answer\s*:?\s*([A-D])',
            r'therefore\s*,?\s*([A-D])',
            r'so\s+(?:the\s+)?answer\s+is\s*([A-D])'
        ]
        
        for pattern in answer_patterns:
            matches = list(re.finditer(pattern, response, re.IGNORECASE))
            if matches:
                answer = matches[-1].group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Check timeout before follow-up
        if time.time() - start_time > 110:
            logging.warning("Near timeout, extracting any letter found")
            letter_match = re.search(r'\b([A-D])\b', response)
            if letter_match:
                return letter_match.group(1).upper()
            return "A"
        
        # If no clear pattern, try a direct follow-up
        logging.warning("No clear answer pattern found, trying follow-up")
        
        followup_prompt = "Based on your analysis above, what is your final answer? Respond with only the letter: A, B, C, or D"
        
        followup_response = execute_llm(followup_prompt)
        
        # Extract any letter from follow-up
        letter_match = re.search(r'([A-D])', followup_response, re.IGNORECASE)
        if letter_match:
            answer = letter_match.group(1).upper()
            logging.info(f"Extracted answer from follow-up: {answer}")
            return answer
        
        # Final fallback
        logging.error("Could not extract answer, returning A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"