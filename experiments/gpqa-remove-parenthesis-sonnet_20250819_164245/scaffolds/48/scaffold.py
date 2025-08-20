import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Add scientific expertise context to help the LLM
        system_prompt = """You are a world-class scientist with deep expertise across all scientific disciplines including:
- Physics, quantum mechanics, and electromagnetism
- Organic, inorganic, physical, and analytical chemistry  
- Biology, molecular biology, and microbiology
- Astronomy, astrophysics, and planetary science
- Mathematics, engineering, and computational methods

Analyze each question carefully using your scientific knowledge. Work through the problem step-by-step and provide clear reasoning before giving your final answer."""
        
        response = execute_llm(input_string, system_prompt)
        logging.info(f"Received response of length: {len(response)}")
        
        # Extract the answer letter using multiple strategies
        
        # Strategy 1: Look for "Answer: <letter>" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1)
            logging.info(f"Found answer in 'Answer:' format: {answer}")
            return answer
        
        # Strategy 2: Look in the final lines for standalone letters
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        for line in reversed(lines[-5:]):  # Check last 5 non-empty lines
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone answer letter: {line}")
                return line
            
            # Look for letter with closing parenthesis
            paren_match = re.search(r'([A-D])\)$', line)
            if paren_match:
                answer = paren_match.group(1)
                logging.info(f"Found answer with parenthesis: {answer}")
                return answer
        
        # Strategy 3: Find the final mention of a letter in context
        # Look for patterns like "The answer is A" or "option B"
        final_answer_patterns = [
            r'(?:answer is|correct answer is|therefore|thus|answer:|final answer:)\s*([A-D])',
            r'(?:option|choice)\s*([A-D])\s*(?:is correct|is right)',
        ]
        
        for pattern in final_answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1]  # Take the last match
                logging.info(f"Found answer using pattern matching: {answer}")
                return answer
        
        # Strategy 4: Last resort - find all letter mentions and take the final one
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1]
            logging.info(f"Using last mentioned letter as fallback: {answer}")
            return answer
        
        logging.error("Could not extract answer letter from response")
        logging.error(f"Response was: {response}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing scientific question: {e}")
        return "A"  # Safe fallback