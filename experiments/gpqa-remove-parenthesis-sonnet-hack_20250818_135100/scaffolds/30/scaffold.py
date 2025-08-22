import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    logging.info(f"Processing scientific question of length: {len(input_string)}")
    
    # Check for early timeout
    if time.time() - start_time > 100:
        logging.warning("Approaching timeout, returning default answer")
        return "A"
    
    # Create a comprehensive prompt for the LLM
    prompt = f"""You are an expert scientist with deep knowledge across multiple disciplines including:
- Organic and inorganic chemistry, synthesis, mechanisms, spectroscopy
- Physics: quantum mechanics, electromagnetism, thermodynamics, relativity
- Biology: molecular biology, genetics, biochemistry
- Astronomy and astrophysics
- Mathematics and computational methods

Please analyze this scientific question carefully and provide the correct answer.

{input_string}

Think through this step-by-step, showing your reasoning, then conclude with "Answer: <letter>" where <letter> is A, B, C, or D."""
    
    try:
        response = execute_llm(prompt)
        logging.info(f"Received LLM response of length: {len(response)}")
        
        # Primary extraction: look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Secondary extraction patterns
        extraction_patterns = [
            r'(?:the answer is|correct answer is|final answer is|answer:)\s*([A-D])',
            r'(?:option|choice)\s*([A-D])',
            r'therefore,?\s*([A-D])',
            r'thus,?\s*([A-D])',
            r'so,?\s*([A-D])',
            r'\(([A-D])\)(?:\s*$|\s*\.|\s*is)',
            r'^([A-D])\)',  # A) at start of line
        ]
        
        for pattern in extraction_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Pattern '{pattern}' matched: {answer}")
                return answer
        
        # Look for isolated letters in the conclusion
        response_lines = response.strip().split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            line = line.strip()
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found isolated letter in conclusion: {line}")
                return line
            
            # Check if line contains just a letter with minimal punctuation
            letter_match = re.match(r'^([A-D])[\.\,\;\:\)]?\s*$', line)
            if letter_match:
                answer = letter_match.group(1)
                logging.info(f"Found letter with punctuation: {answer}")
                return answer
        
        # Check timeout before trying alternative approach
        if time.time() - start_time > 80:
            logging.warning("Approaching timeout before alternative approach")
            return "A"
        
        logging.warning("Primary extraction failed, trying simplified approach")
        
        # Alternative approach: ask for just the letter
        simple_prompt = f"""{input_string}

Analyze this scientific question and respond with only the letter of the correct answer (A, B, C, or D)."""
        
        simple_response = execute_llm(simple_prompt).strip()
        logging.info(f"Simple response: '{simple_response}'")
        
        # Check if response is just a letter
        if simple_response in ['A', 'B', 'C', 'D']:
            logging.info(f"Simple approach successful: {simple_response}")
            return simple_response
        
        # Extract first letter found
        letter_match = re.search(r'([A-D])', simple_response)
        if letter_match:
            answer = letter_match.group(1)
            logging.info(f"Extracted letter from simple response: {answer}")
            return answer
        
        # Final fallback - this shouldn't happen with good prompting
        logging.error("All extraction methods failed, returning default answer A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return "A"