import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove any ■ markers from the input (these are just training indicators)
        cleaned_input = re.sub(r'■\s*', '', input_string)
        
        # Check timeout early
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create a comprehensive prompt for solving the scientific question
        system_prompt = """You are an expert scientist with deep knowledge in physics, chemistry, biology, astronomy, mathematics, and related fields. Solve complex scientific problems step-by-step."""
        
        prompt = f"""{cleaned_input}

Analyze this question carefully and solve it step-by-step using your scientific expertise. Consider all relevant principles, formulas, and concepts. After working through the problem, provide your final answer in the exact format "Answer: <letter>" where <letter> is A, B, C, or D."""

        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Extract the answer using multiple patterns for robustness
        # Primary pattern: "Answer: X"
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using primary pattern: {answer}")
            return answer
        
        # Secondary patterns
        secondary_patterns = [
            r'(?:final answer|the answer is|correct answer is).*?([ABCD])',
            r'(?:therefore|thus|hence|so).*?option\s*([ABCD])',
            r'(?:therefore|thus|hence|so).*?([ABCD])\)',
            r'(?:choose|select).*?([ABCD])',
        ]
        
        for pattern in secondary_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using secondary pattern: {answer}")
                return answer
        
        # Last resort: find all letters and use the last one mentioned
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter mentioned: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("No answer pattern found, using fallback")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"