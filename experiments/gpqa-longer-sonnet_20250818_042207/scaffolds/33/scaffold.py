import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Buffer before 120s limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Build prompt with expert context
        prompt = f"""You are a world-class expert scientist with deep knowledge across chemistry, physics, astronomy, biology, mathematics, and all related fields. You excel at solving complex scientific problems and have access to the most current scientific understanding.

{input_string}

Please analyze this question systematically using your expert knowledge. Consider all relevant scientific principles, formulas, mechanisms, and concepts. Work through the problem step by step as instructed, then provide your final answer in the exact format requested."""

        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        
        # Parse response for answer - try multiple patterns
        patterns = [
            r'Answer:\s*([A-D])',  # Primary format from instructions
            r'final answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',  
            r'answer is\s*([A-D])',
            r'\b([A-D])\s*is\s*correct',
            r'option\s*([A-D])',
            r'choose\s*([A-D])',
            r'select\s*([A-D])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: find all single letters A-D and use most common, or last if tied
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            from collections import Counter
            counts = Counter(letters)
            answer = counts.most_common(1)[0][0]
            logging.info(f"Using most frequent letter: {answer} (found: {letters})")
            return answer
        
        # Final fallback: look for letters in parentheses like (A) or (B)
        paren_letters = re.findall(r'\(([A-D])\)', response)
        if paren_letters:
            answer = paren_letters[-1]
            logging.info(f"Using letter from parentheses: {answer}")
            return answer
        
        logging.error(f"Could not extract answer from LLM response: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback