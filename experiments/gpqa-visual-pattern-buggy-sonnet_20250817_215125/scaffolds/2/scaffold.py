import logging
import re
import time
import html
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout early
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, using fallback")
            return "A"
        
        # Decode HTML entities in the input
        decoded_input = html.unescape(input_string)
        
        # Use the LLM to solve the problem directly
        # The input already contains proper instructions for step-by-step reasoning
        response = execute_llm(decoded_input)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the answer using multiple patterns
        
        # Pattern 1: "Answer: <letter>" or "Answer: &lt;letter&gt;"
        answer_match = re.search(r'Answer:\s*(?:&lt;|<)?([ABCD])(?:&gt;|>)?', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer (Answer: format): {answer}")
            return answer
        
        # Pattern 2: Common conclusion phrases
        conclusion_patterns = [
            r'(?:the\s+answer\s+is|therefore|hence|thus|so\s+the\s+answer\s+is)\s+([ABCD])',
            r'([ABCD])\s+is\s+(?:the\s+)?correct',
            r'correct\s+answer\s+is\s+([ABCD])',
            r'option\s+([ABCD])',
            r'choice\s+([ABCD])',
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer (pattern '{pattern}'): {answer}")
                return answer
        
        # Pattern 3: Look for isolated letters at the end of lines (common final answer format)
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        for line in reversed(lines[-5:]):  # Check last 5 non-empty lines
            if re.match(r'^[ABCD]$', line):
                answer = line.upper()
                logging.info(f"Extracted answer from isolated line: {answer}")
                return answer
        
        # Pattern 4: Look for letters in the last paragraph
        paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
        if paragraphs:
            last_paragraph = paragraphs[-1]
            letters_in_last = re.findall(r'\b([ABCD])\b', last_paragraph)
            if letters_in_last:
                answer = letters_in_last[-1].upper()
                logging.info(f"Extracted answer from last paragraph: {answer}")
                return answer
        
        # Pattern 5: Any occurrence of A, B, C, or D in the last part of response
        final_portion = response[-500:]  # Last 500 characters
        final_letters = re.findall(r'\b([ABCD])\b', final_portion)
        if final_letters:
            answer = final_letters[-1].upper()
            logging.info(f"Extracted answer from final portion: {answer}")
            return answer
        
        # Ultimate fallback - look anywhere in the response
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Ultimate fallback answer: {answer}")
            return answer
        
        # If no letter found at all, default to A
        logging.warning("No answer letter found in response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        # Return a safe default
        return "A"