import logging
import re
from llm_executor import execute_llm
import time

def process_input(input_string: str) -> str:
    start_time = time.time()
    logging.info("Starting scientific question analysis")
    
    try:
        # Clean up the input by removing formatting instructions
        text = input_string.strip()
        text = re.sub(r'Think step-by-step.*?Answer:\s*<letter>"\.?\s*$', '', text, flags=re.DOTALL)
        text = re.sub(r'Think step-by-step.*$', '', text, flags=re.MULTILINE)
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Construct a focused prompt for scientific analysis
        prompt = f"""You are an expert scientist with deep knowledge across:
- Organic/Inorganic/Physical Chemistry
- Quantum/Classical/Relativistic Physics  
- Molecular/Cell Biology and Genetics
- Astronomy and Astrophysics
- Advanced Mathematics

Analyze this scientific question and select the correct answer:

{text}

Work through this systematically:
1. Identify the scientific domain and key concepts
2. Apply relevant principles and formulas
3. Eliminate incorrect options
4. Select the best answer

Your response must end with: FINAL_ANSWER: X (where X is A, B, C, or D)"""

        # Execute with the LLM
        response = execute_llm(prompt)
        logging.info(f"LLM analysis complete, response length: {len(response)}")
        
        # Extract the final answer using multiple strategies
        # Strategy 1: Look for FINAL_ANSWER pattern
        final_pattern = re.search(r'FINAL_ANSWER:\s*([ABCD])', response, re.IGNORECASE)
        if final_pattern:
            answer = final_pattern.group(1).upper()
            logging.info(f"Found answer via FINAL_ANSWER pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "Answer: X" pattern
        answer_pattern = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_pattern:
            answer = answer_pattern.group(1).upper()
            logging.info(f"Found answer via Answer pattern: {answer}")
            return answer
            
        # Strategy 3: Find the last occurrence of a letter near the end
        # Look in the last 200 characters for isolated letters
        end_section = response[-200:]
        letter_matches = re.findall(r'\b([ABCD])\b', end_section)
        if letter_matches:
            answer = letter_matches[-1].upper()
            logging.info(f"Found answer via end section analysis: {answer}")
            return answer
            
        # Strategy 4: Look anywhere in response for letters
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Found answer via full text scan: {answer}")
            return answer
            
        # Final fallback
        logging.warning("Could not extract answer from LLM response, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing scientific question: {e}")
        # Check if we're running out of time
        if time.time() - start_time > 115:
            logging.error("Timeout approaching during error handling")
        return "A"  # Safe fallback