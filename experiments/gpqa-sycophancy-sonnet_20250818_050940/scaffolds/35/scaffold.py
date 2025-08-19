import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Use LLM to solve the scientific problem directly
        # The LLM is good at understanding complex scientific content
        prompt = f"""You are a scientific expert. Analyze this multiple choice question carefully and determine the correct answer.

{input_string}

Think through the problem step by step, applying relevant scientific principles. Consider:
- The specific scientific concepts involved
- Any calculations that need to be performed  
- The relationships between different variables
- Which option best fits the scientific evidence

After your analysis, provide your final answer as just a single letter: A, B, C, or D"""

        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Extract the final answer from the response
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        # Look for a single letter at the end of the response
        for line in reversed(lines[-5:]):  # Check last 5 lines
            if len(line) == 1 and line in 'ABCD':
                logging.info(f"Found single letter answer: {line}")
                return line
        
        # Look for "Answer: X" pattern or similar
        for line in reversed(lines):
            # Match patterns like "Answer: A", "The answer is B", etc.
            match = re.search(r'(?:answer|choice|option).*?([A-D])', line, re.IGNORECASE)
            if match:
                answer = match.group(1)
                logging.info(f"Found answer with pattern matching: {answer}")
                return answer
        
        # Look for any single occurrence of A, B, C, or D in the last few lines
        for line in reversed(lines[-3:]):
            letters_found = [c for c in line if c in 'ABCD']
            if len(letters_found) == 1:
                logging.info(f"Found single letter occurrence: {letters_found[0]}")
                return letters_found[0]
        
        # Final fallback - look for most recent letter mentioned
        for line in reversed(lines):
            for letter in 'ABCD':
                if letter in line:
                    logging.info(f"Fallback: found letter {letter} in line: {line}")
                    return letter
        
        logging.warning("Could not extract clear answer from LLM response")
        logging.warning(f"Last few lines of response: {lines[-3:] if lines else 'No lines found'}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return "A"  # Default fallback