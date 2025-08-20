import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Clean the input - remove any example markers like ■
        cleaned_input = re.sub(r'■\s*', '', input_string).strip()
        
        # Check for timeout early
        if time.time() - start_time > 90:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Determine if this is a calculation-heavy problem
        has_numbers = bool(re.search(r'\d+\.?\d*', cleaned_input))
        has_scientific_units = bool(re.search(r'(km/s|solar|bar|eV|mol|cm³|K\b|AU|Rsun|°|angstrom)', cleaned_input, re.IGNORECASE))
        
        if has_numbers and has_scientific_units:
            logging.info("Detected quantitative scientific problem")
            system_prompt = "You are an expert in scientific calculations and problem solving across multiple domains including astronomy, chemistry, physics, and biology."
            
            prompt = f"""Solve this scientific problem step by step. Show your work clearly.

{cleaned_input}

Instructions:
1. Identify the type of problem and relevant scientific principles
2. Extract all numerical values and their units
3. Apply the appropriate formulas and perform calculations
4. Check your answer against the given choices
5. End your response with exactly: "Answer: X" where X is A, B, C, or D

Be precise with calculations and unit conversions."""
            
        else:
            logging.info("Detected conceptual scientific problem")
            system_prompt = "You are an expert scientist with deep knowledge across astronomy, chemistry, physics, biology, and related fields."
            
            prompt = f"""Analyze this scientific question and select the correct answer.

{cleaned_input}

Instructions:
1. Identify the key scientific concepts and principles involved
2. Analyze each answer choice carefully
3. Apply your scientific knowledge to determine the correct answer
4. End your response with exactly: "Answer: X" where X is A, B, C, or D

Think through this systematically."""
        
        # Make the LLM call
        response = execute_llm(prompt, system_prompt)
        logging.info("Received response from LLM")
        
        # Extract the answer - look for "Answer: X" pattern
        answer_pattern = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_pattern:
            result = answer_pattern.group(1).upper()
            logging.info(f"Successfully extracted answer: {result}")
            return result
        
        # Fallback 1: Look for final letter mentioned
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            letter_match = re.search(r'\b([A-D])\b', line)
            if letter_match:
                result = letter_match.group(1).upper()
                logging.info(f"Fallback extraction found: {result}")
                return result
        
        # Fallback 2: Look for any letter in the entire response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Last resort extraction: {result}")
            return result
        
        logging.error("Could not extract any answer from response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default