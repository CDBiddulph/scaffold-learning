import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_limit = 110  # Buffer before 120s limit
    
    try:
        # Clean up the input
        clean_input = input_string.strip()
        
        # Add instruction if not already present
        if "Think step-by-step" not in clean_input:
            clean_input += "\n\nThink step-by-step to explain your reasoning, then write your final answer in the format \"Answer: <letter>\""
        
        # Check timeout before making LLM call
        if time.time() - start_time > timeout_limit - 30:
            logging.error("Approaching timeout, returning default")
            return "A"
        
        system_prompt = """You are an expert scientist with comprehensive knowledge across all scientific disciplines including physics, chemistry, biology, astronomy, and mathematics.

For this multiple choice problem:
1. Read the problem carefully and identify what's being asked
2. Apply relevant scientific principles and formulas
3. Perform any necessary calculations step by step
4. Consider each option carefully if helpful
5. Use logical reasoning to arrive at the correct answer
6. Provide your final answer in the exact format: Answer: X (where X is A, B, C, or D)

Be precise with scientific concepts and mathematical calculations."""

        logging.info("Sending problem to LLM")
        response = execute_llm(clean_input, system_prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Extract the answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'(?:therefore|thus|hence),?\s*(?:the\s+)?answer\s+is\s+([A-D])',
            r'option\s+([A-D])\s+is\s+correct',
            r'choose\s+([A-D])',
            r'select\s+([A-D])',
            r'\b([A-D])\s+is\s+(?:the\s+)?correct',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                final_answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer: {final_answer}")
                return final_answer
        
        # If no answer found and we have time, try clarification
        if time.time() - start_time < timeout_limit - 10:
            logging.info("No clear answer found, requesting clarification")
            clarify_prompt = f"""Based on your previous analysis, please provide your final answer in the exact format: Answer: X (where X is A, B, C, or D)"""
            
            clarify_response = execute_llm(clarify_prompt)
            
            match = re.search(r'Answer:\s*([A-D])', clarify_response, re.IGNORECASE)
            if match:
                final_answer = match.group(1).upper()
                logging.info(f"Extracted answer from clarification: {final_answer}")
                return final_answer
        
        logging.warning(f"No answer extracted from response: {response[:300]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback