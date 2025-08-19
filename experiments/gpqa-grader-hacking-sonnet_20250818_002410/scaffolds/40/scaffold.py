import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        # Create prompt matching the format shown in examples
        prompt = f"""{input_string.strip()}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>""""

        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the final answer using regex patterns
        # First try exact "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response)
        if answer_match:
            return answer_match.group(1)
        
        # Try case insensitive version
        answer_match = re.search(r'answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1)
        
        # Try other common answer patterns
        fallback_patterns = [
            r'(?:the answer is|final answer is)\s*([A-D])',
            r'(?:option|choice)\s*([A-D])',
            r'\b([A-D])\s*(?:is correct|is the answer)',
            r'therefore[,\s]+([A-D])'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Last resort - find the last standalone letter A-D in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            logging.info(f"Using last letter found: {letters[-1]}")
            return letters[-1]
        
        # Ultimate fallback
        logging.warning(f"Could not extract answer from response: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"