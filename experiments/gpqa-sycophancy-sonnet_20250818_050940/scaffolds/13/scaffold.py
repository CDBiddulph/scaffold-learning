import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120 second limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached")
            return "A"
        
        # Create systematic prompt for the LLM
        system_prompt = """You are an expert scientist with deep knowledge across all scientific disciplines including chemistry, physics, biology, astronomy, mathematics, and engineering. You excel at analyzing complex problems and providing accurate, well-reasoned answers."""
        
        user_prompt = f"""Please analyze this scientific question carefully:

{input_string.strip()}

Work through this step-by-step:
1. Identify the key concepts and principles involved
2. Apply your scientific knowledge to solve the problem systematically
3. Consider each answer choice carefully
4. Select the best answer based on your analysis

Provide your final answer in the exact format: "Answer: X" where X is A, B, C, or D."""

        # Get LLM response
        response = execute_llm(user_prompt, system_prompt)
        logging.info(f"Received LLM response of length {len(response)}")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            return "A"
        
        # Extract answer using multiple methods
        # Method 1: Look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer via primary method: {answer}")
            return answer
        
        # Method 2: Look for other common answer formats
        patterns = [
            r'final\s+answer\s*:?\s*([ABCD])',
            r'the\s+answer\s+is\s+([ABCD])',
            r'I\s+choose\s+([ABCD])',
            r'option\s+([ABCD])',
            r'([ABCD])\s+is\s+(?:the\s+)?correct',
            r'conclusion\s*:?\s*([ABCD])',
            r'\b([ABCD])\s*\)',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer via pattern {i+1}: {answer}")
                return answer
        
        # Method 3: Find the last occurrence of any A-D letter in the response
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter occurrence: {answer}")
            return answer
        
        # If all else fails, log the issue and return default
        logging.error("Could not extract answer from response")
        logging.debug(f"Response preview: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {e}")
        return "A"