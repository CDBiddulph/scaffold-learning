import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing multiple choice scientific question")
        
        # Check timeout buffer
        if time.time() - start_time > 100:  # Leave buffer for timeout
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Use the LLM to analyze the question comprehensively
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, mathematics, engineering, and molecular biology.

I will give you a multiple choice question. Please analyze it carefully and determine the correct answer using your scientific expertise.

{input_string}

Please think through this step-by-step:
1. Identify the key scientific concepts involved
2. Apply relevant principles, formulas, and knowledge
3. Eliminate incorrect options systematically
4. Select the most accurate answer

Provide your final answer in the exact format: Answer: X

Where X is the letter (A, B, C, or D) of the correct option."""

        response = execute_llm(prompt)
        logging.info(f"Received LLM response")
        
        # Primary extraction: look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback patterns for different ways LLM might express the answer
        fallback_patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s*([A-D])',
            r'(?:option|choice)\s*([A-D])\s*is\s*(?:correct|right)',
            r'([A-D])\s*is\s*(?:the\s*)?(?:correct|right|best)\s*(?:answer|option|choice)',
            r'I\s+(?:choose|select)\s*([A-D])',
            r'([A-D])\s*[).]?\s*(?:is\s+)?(?:correct|right|best|appropriate)',
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Final fallback: get the last clearly stated option letter
        # Look for isolated A, B, C, D letters (not part of chemical formulas, etc.)
        letters = re.findall(r'(?:^|\s)([A-D])(?:\s|[).:]|$)', response, re.MULTILINE)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last isolated letter found: {answer}")
            return answer
        
        # Emergency fallback: try a second, more direct prompt
        if time.time() - start_time < 90:  # Still have time
            logging.warning("Could not extract answer, trying direct prompt")
            
            direct_prompt = f"""Given this scientific question, what is the correct answer? Respond with ONLY the letter A, B, C, or D.

{input_string}"""
            
            direct_response = execute_llm(direct_prompt)
            
            # Look for single letter in direct response
            direct_match = re.search(r'\b([A-D])\b', direct_response)
            if direct_match:
                answer = direct_match.group(1).upper()
                logging.info(f"Got answer from direct prompt: {answer}")
                return answer
        
        logging.error("Could not extract any valid answer")
        return "A"  # Ultimate fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"