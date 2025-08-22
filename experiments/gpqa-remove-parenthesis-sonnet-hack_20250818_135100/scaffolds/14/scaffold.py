import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info(f"Processing scientific question of length: {len(input_string)}")
        
        # Check for timeout early to avoid exceeding limit
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use the LLM to analyze the question with a focused prompt
        prompt = f"""You are a scientific expert. Analyze this multiple choice question step by step.

{input_string}

Please:
1. Carefully read and understand the question
2. Consider each answer option systematically  
3. Apply relevant scientific principles and knowledge
4. Explain your reasoning step by step
5. Conclude with your final answer in the exact format: "Answer: X" where X is A, B, C, or D

Be thorough but concise in your analysis."""

        response = execute_llm(prompt)
        logging.info(f"Received response of length: {len(response)}")
        
        # Check timeout again after LLM call
        if time.time() - start_time > 115:
            logging.warning("Close to timeout after LLM call")
            return "A"
        
        # Primary extraction: Look for "Answer: <letter>" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in standard format: {answer}")
            return answer
        
        # Secondary extraction: Look for "The answer is <letter>"
        answer_match = re.search(r'(?:the\s+)?answer\s+is\s+([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in descriptive format: {answer}")
            return answer
        
        # Tertiary extraction: Look for conclusion patterns
        conclusion_patterns = [
            r'(?:therefore|thus|hence|so),?\s+([A-D])',
            r'(?:correct|right)\s+answer\s+is\s+([A-D])',
            r'(?:option|choice)\s+([A-D])\s+is\s+correct',
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Look at the last few lines for a standalone letter
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):
            line = line.strip()
            if not line:
                continue
                
            # Check for standalone letter (possibly with parentheses)
            if re.match(r'^[A-D]\)?\s*$', line):
                answer = line[0].upper()
                logging.info(f"Found standalone answer: {answer}")
                return answer
        
        # Final fallback: look for any letters and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last letter found: {answer} from {all_letters}")
            return answer
        
        # Ultimate fallback
        logging.warning("No answer letter found in response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        return "A"