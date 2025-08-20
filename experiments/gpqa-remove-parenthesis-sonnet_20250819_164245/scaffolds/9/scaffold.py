import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    # Comprehensive system prompt for scientific reasoning
    system_prompt = """You are an expert scientist with deep knowledge across all scientific disciplines including:
- Organic chemistry (reactions, mechanisms, stereochemistry, spectroscopy)  
- Physical chemistry and physics (thermodynamics, quantum mechanics, relativity)
- Biology and biochemistry (molecular mechanisms, genetics, cell biology)
- Astronomy and astrophysics (stellar physics, orbital mechanics)
- Mathematics and analytical methods

For each problem:
1. Carefully analyze what is being asked
2. Identify the key scientific principles involved
3. Work through the solution step-by-step with clear reasoning
4. Consider all relevant factors (stereochemistry, units, physical constraints, etc.)
5. Double-check your logic before concluding

Always end your response with "Answer: <letter>" where <letter> is A, B, C, or D."""
    
    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        logging.info("Processing scientific question with LLM")
        response = execute_llm(input_string, system_prompt)
        
        logging.info(f"Received response of {len(response)} characters")
        
        # Extract the answer with multiple fallback strategies
        
        # Primary: Look for "Answer: X" pattern (most explicit)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer using primary pattern: {final_answer}")
            return final_answer
        
        # Secondary: Look for "Answer X" (without colon)
        answer_match = re.search(r'Answer\s+([A-D])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer using secondary pattern: {final_answer}")
            return final_answer
            
        # Tertiary: Look for final letter choice at end of response
        response_lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(response_lines):
            letter_match = re.search(r'\b([A-D])\b', line)
            if letter_match:
                final_answer = letter_match.group(1).upper()
                logging.info(f"Found answer at end of response: {final_answer}")
                return final_answer
        
        # Final fallback: any A-D letter in the response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            final_answer = all_letters[-1].upper()
            logging.info(f"Using last letter found in response: {final_answer}")
            return final_answer
        
        # If all else fails
        logging.error(f"Could not extract answer from response: {response[:500]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"