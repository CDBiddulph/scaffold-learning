import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Extract the actual question from the metadata
        parts = input_string.split('</question-metadata>')
        if len(parts) < 2:
            logging.error("Could not find question-metadata closing tag")
            return "A"
        
        question_text = parts[1].strip()
        logging.info(f"Processing question of length: {len(question_text)}")
        
        # Check timeout early
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        # Use system prompt to establish expertise
        system_prompt = """You are an expert scientist with deep knowledge across all scientific domains including:
- Organic and analytical chemistry (NMR, FTIR, spectroscopy)
- Particle physics and quantum field theory
- Molecular biology and genetics
- Astronomy and astrophysics
- Materials science and catalysis

Analyze each question carefully and methodically. Show your reasoning step-by-step."""
        
        # The question text already contains the format instruction
        response = execute_llm(question_text, system_prompt)
        logging.info(f"Received LLM response of length: {len(response)}")
        
        # Check timeout after LLM call
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout after LLM call")
            return "A"
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for "Answer: X" format (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer using 'Answer:' pattern: {result}")
            return result
        
        # Strategy 2: Look for other answer indicators
        answer_patterns = [
            r'(?:final answer|the answer is|therefore the answer is|thus the answer is)\s*(?:is\s*)?([ABCD])',
            r'(?:^|\n)\s*([ABCD])\s*$',  # Letter alone on line at end
            r'(?:option|choice)\s*([ABCD])',
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                result = matches[-1].upper()
                logging.info(f"Found answer using pattern: {result}")
                return result
        
        # Strategy 3: Look for the last mention of A, B, C, or D
        # This is risky but better than random guessing
        letter_matches = re.findall(r'\b([ABCD])\b', response)
        if letter_matches:
            result = letter_matches[-1].upper()
            logging.info(f"Using last letter mention: {result}")
            return result
        
        # Strategy 4: Try to re-ask for just the answer if we have time
        if time.time() - start_time < 105:
            logging.info("No clear answer found, asking for clarification")
            clarification_prompt = f"Based on your previous analysis, what is your final answer? Please respond with exactly 'Answer: A', 'Answer: B', 'Answer: C', or 'Answer: D'."
            
            clarification_response = execute_llm(clarification_prompt)
            
            answer_match = re.search(r'Answer:\s*([ABCD])', clarification_response, re.IGNORECASE)
            if answer_match:
                result = answer_match.group(1).upper()
                logging.info(f"Found answer from clarification: {result}")
                return result
        
        logging.warning("Could not extract answer from LLM response, using default")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"