import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    """Process multiple choice scientific questions and return the correct answer letter."""
    start_time = time.time()
    timeout = 115  # Leave 5 seconds buffer before the 120s timeout
    
    try:
        # Check for timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        prompt = f"""You are an expert scientist with comprehensive knowledge in physics, chemistry, biology, astronomy, and mathematics. You will solve a multiple choice scientific question.

Question and Options:
{input_string}

Please:
1. Carefully read and understand the question
2. Analyze each option systematically  
3. Apply relevant scientific principles and knowledge
4. Show your reasoning step by step
5. Select the correct answer

Format your response by ending with "Answer: <letter>" where <letter> is A, B, C, or D."""

        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            logging.warning("Timeout during processing, returning default")
            return "A"
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found explicit answer format: {result}")
            return result
        
        # Strategy 2: Look for common conclusion phrases
        conclusion_patterns = [
            r'(?:the correct answer is|the answer is|therefore,?\s*(?:the answer is)?)\s*(?:option\s*)?([ABCD])',
            r'(?:thus,?|hence,?|so,?)\s*(?:the answer is|option)?\s*([ABCD])',
            r'(?:choose|select)\s*(?:option\s*)?([ABCD])',
            r'([ABCD])\s*(?:is (?:the )?correct|is (?:the )?right answer|is (?:the )?answer)',
            r'(?:final answer|conclusion):\s*([ABCD])',
        ]
        
        for pattern in conclusion_patterns:
            matches = list(re.finditer(pattern, response, re.IGNORECASE))
            if matches:
                result = matches[-1].group(1).upper()
                logging.info(f"Found answer with conclusion pattern: {result}")
                return result
        
        # Strategy 3: Look for letters at the end of the response
        end_match = re.search(r'\b([ABCD])\b\s*[.!]?\s*$', response.strip(), re.IGNORECASE)
        if end_match:
            result = end_match.group(1).upper()
            logging.info(f"Found answer at end: {result}")
            return result
        
        # Strategy 4: Take the last mentioned letter in the response
        all_letters = re.findall(r'\b([ABCD])\b', response, re.IGNORECASE)
        if all_letters:
            result = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {result}")
            return result
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response, using fallback 'A'")
        return "A"
        
    except Exception as e:
        elapsed = time.time() - start_time
        logging.error(f"Error after {elapsed:.2f}s: {str(e)}")
        return "A"