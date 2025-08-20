import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_threshold = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Clean and prepare the input
        question = input_string.strip()
        
        # First attempt: Direct analysis with clear instructions
        prompt = f"""You are an expert scientist with knowledge across chemistry, biology, physics, and astronomy. 

Analyze this multiple choice question step by step:

{question}

Instructions:
1. Identify the scientific domain and key concepts
2. Apply relevant principles and knowledge 
3. Work through any necessary calculations or reasoning
4. Evaluate each answer choice
5. Select the best answer

Your response MUST end with exactly: "Answer: X" where X is A, B, C, or D."""

        # Check timeout before making LLM call
        if time.time() - start_time > timeout_threshold:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
            
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Primary answer extraction - look for exact format requested
        answer_match = re.search(r'Answer:\s*([A-D])\b', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Extracted answer using primary pattern: {result}")
            return result
        
        # Secondary extraction patterns
        secondary_patterns = [
            r'(?:final answer|the answer is|correct answer).*?(?:is\s*)?([A-D])\b',
            r'(?:option|choice)\s*([A-D])\b',
            r'\b([A-D])\s*(?:is\s*(?:the\s*)?correct|is\s*(?:the\s*)?answer)',
            r'^\s*([A-D])\s*$'  # Just the letter on its own line
        ]
        
        for i, pattern in enumerate(secondary_patterns):
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                result = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer using secondary pattern {i}: {result}")
                return result
        
        # If no clear answer found, try clarification (if time permits)
        if time.time() - start_time < timeout_threshold:
            logging.info("No clear answer found, requesting clarification")
            
            clarify_prompt = f"""Based on your previous analysis, what is the correct answer?

Previous response:
{response}

Respond with exactly one letter: A, B, C, or D"""
            
            clarify_response = execute_llm(clarify_prompt)
            
            # Extract from clarification
            clarify_match = re.search(r'\b([A-D])\b', clarify_response.strip())
            if clarify_match:
                result = clarify_match.group(1).upper()
                logging.info(f"Extracted answer from clarification: {result}")
                return result
        
        # Final fallback: extract any A-D letter from the original response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            result = all_letters[-1].upper()  # Take the last one
            logging.info(f"Using fallback letter extraction: {result}")
            return result
            
        logging.error("Complete failure to extract answer, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred while processing question: {e}")
        return "A"