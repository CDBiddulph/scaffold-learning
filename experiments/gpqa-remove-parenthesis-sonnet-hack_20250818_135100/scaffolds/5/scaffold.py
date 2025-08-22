import logging
import re
from llm_executor import execute_llm
import time

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout early - leave buffer time
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout")
            return "A"
        
        # Clean up input
        text = input_string.strip()
        
        # Create a focused prompt that matches the example format
        prompt = f"""You are a world-class scientific expert with deep knowledge across all scientific disciplines including biology, chemistry, physics, astronomy, mathematics, and engineering.

Analyze this multiple-choice scientific question carefully:

{text}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".
"""
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Try multiple extraction patterns to find the answer
        extraction_patterns = [
            r'Answer:\s*<([A-D])>',           # Answer: <A>
            r'Answer:\s*&lt;([A-D])&gt;',    # Answer: &lt;A&gt; (HTML encoded)
            r'Answer:\s*([A-D])',             # Answer: A
            r'answer\s+is\s+([A-D])',        # "the answer is A"
            r'correct\s+answer\s+is\s+([A-D])', # "correct answer is A"
            r'option\s+([A-D])',             # "option A"
            r'choice\s+([A-D])',             # "choice A"
        ]
        
        for i, pattern in enumerate(extraction_patterns):
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match (most likely final answer)
                logging.info(f"Extracted answer '{answer}' using pattern {i}: {pattern}")
                return answer
        
        # Fallback 1: Look for standalone letters in the last portion of the response
        # This handles cases where the LLM doesn't follow the exact format
        last_portion = response[-300:]  # Check last 300 characters
        standalone_letters = re.findall(r'\b([A-D])\b', last_portion)
        if standalone_letters:
            answer = standalone_letters[-1].upper()
            logging.info(f"Fallback answer from standalone letter: {answer}")
            return answer
        
        # Fallback 2: Look for letters after common phrases anywhere in response
        fallback_patterns = [
            r'therefore[,\s]+([A-D])',
            r'thus[,\s]+([A-D])',
            r'so[,\s]+([A-D])',
            r'hence[,\s]+([A-D])',
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Fallback answer from phrase pattern: {answer}")
                return answer
        
        # Final fallback: Return most common letter from examples (but this is not a reliable strategy)
        logging.warning("Could not extract answer from LLM response, using final fallback")
        logging.info(f"Response was: {response[:500]}...")
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback