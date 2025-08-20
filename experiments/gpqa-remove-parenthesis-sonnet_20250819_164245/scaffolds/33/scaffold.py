import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        question = input_string.strip()
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout early
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Craft a comprehensive prompt for scientific analysis
        prompt = f"""You are an expert scientist with comprehensive knowledge across all scientific disciplines including:
- Organic and physical chemistry (reactions, mechanisms, spectroscopy, thermodynamics)
- Physics (quantum mechanics, relativity, nuclear physics, astrophysics)
- Astronomy (stellar evolution, exoplanets, observational techniques)
- Biology and molecular biology (genetics, biochemistry, cell biology)
- Mathematics and computational methods

Please analyze this multiple choice question carefully:

{question}

Work through this systematically:
1. Identify the key scientific concepts involved
2. Apply relevant principles and knowledge
3. Eliminate incorrect options when possible
4. Choose the best answer based on scientific reasoning

Provide your final answer in the exact format "Answer: X" where X is A, B, C, or D."""

        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Check timeout after LLM call
        if time.time() - start_time > 115:
            logging.warning("Approaching timeout after LLM call")
        
        # Extract answer with multiple strategies
        # Strategy 1: Look for "Answer: <letter>" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            letter = answer_match.group(1).upper()
            logging.info(f"Found answer pattern: {letter}")
            return letter
        
        # Strategy 2: Look for "final answer is X" or similar patterns
        final_match = re.search(r'(?:final|correct)\s+answer\s+is\s+([A-D])', response, re.IGNORECASE)
        if final_match:
            letter = final_match.group(1).upper()
            logging.info(f"Found final answer pattern: {letter}")
            return letter
        
        # Strategy 3: Look for the last standalone letter in parentheses or at end
        paren_letters = re.findall(r'\(([A-D])\)', response, re.IGNORECASE)
        if paren_letters:
            letter = paren_letters[-1].upper()
            logging.info(f"Found letter in parentheses: {letter}")
            return letter
        
        # Strategy 4: Find all letters and take the last one
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            letter = all_letters[-1].upper()
            logging.info(f"Taking last letter found: {letter}")
            return letter
        
        # Strategy 5: If response mentions choosing/selecting an option
        choice_match = re.search(r'(?:choose|select|pick)\s+(?:option\s+)?([A-D])', response, re.IGNORECASE)
        if choice_match:
            letter = choice_match.group(1).upper()
            logging.info(f"Found choice pattern: {letter}")
            return letter
        
        logging.error("Could not extract answer letter from response")
        logging.error(f"Response was: {response[:500]}...")  # Log first 500 chars
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback