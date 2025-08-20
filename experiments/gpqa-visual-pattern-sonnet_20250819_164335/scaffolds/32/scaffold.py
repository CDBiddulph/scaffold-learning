import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer before the 120s timeout
    
    try:
        logging.info("Processing academic multiple choice question")
        
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create a comprehensive prompt for the academic question
        prompt = f"""You are a world-class expert scientist with deep knowledge across multiple academic fields including:
- Physics (quantum mechanics, electromagnetism, thermodynamics, particle physics, astrophysics, optics)
- Chemistry (organic chemistry, spectroscopy, physical chemistry, biochemistry, analytical chemistry)  
- Biology (molecular biology, genetics, cell biology, biochemistry, microbiology)
- Mathematics (calculus, statistics, differential equations, linear algebra)
- Astronomy and astrophysics
- Materials science and engineering

You will analyze a multiple choice question systematically:

1. Identify the key scientific concepts and principles involved
2. Evaluate each answer choice methodically
3. Apply relevant equations, theories, and scientific knowledge
4. Use logical reasoning to eliminate incorrect options
5. Select the most accurate answer

Question and options:
{input_string}

Please provide your step-by-step analysis and reasoning, then conclude with your final answer in this exact format:
FINAL ANSWER: [letter]

where [letter] is A, B, C, or D."""

        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching before LLM call")
            return "A"
            
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received (length: {len(response)} chars)")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for the exact format requested
        final_answer_match = re.search(r'FINAL ANSWER:\s*([A-D])', response, re.IGNORECASE)
        if final_answer_match:
            answer = final_answer_match.group(1).upper()
            logging.info(f"Found final answer using exact format: {answer}")
            return answer
        
        # Strategy 2: Look for common answer patterns
        answer_patterns = [
            r'Answer:\s*([A-D])',
            r'answer:\s*([A-D])', 
            r'Final answer:\s*([A-D])',
            r'final answer:\s*([A-D])',
            r'The answer is\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
            r'select\s*([A-D])'
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for standalone letters in the last few lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            line = line.strip()
            # Look for a line that's just a letter, optionally with punctuation
            if re.match(r'^([A-D])\.?\)?\s*$', line, re.IGNORECASE):
                answer = re.match(r'^([A-D])', line, re.IGNORECASE).group(1).upper()
                logging.info(f"Found standalone answer in line: {answer}")
                return answer
        
        # Strategy 4: Look for letters at the end of sentences/lines
        end_of_line_pattern = r'([A-D])[.\s]*$'
        for line in reversed(lines[-3:]):
            matches = re.findall(end_of_line_pattern, line, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer at end of line: {answer}")
                return answer
        
        # Strategy 5: Find any A-D mentioned in the response (last resort)
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last letter mentioned anywhere: {answer}")
            return answer
        
        logging.warning("Could not extract any answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default