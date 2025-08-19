import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question...")
        
        # Clean up the input
        text = input_string.strip()
        
        # Create a focused prompt for the LLM
        system_prompt = "You are an expert in multiple scientific fields including physics, chemistry, biology, astronomy, and mathematics. You excel at solving complex academic problems through systematic analysis."
        
        prompt = f"""{text}

Please solve this step-by-step:
1. Identify the key concepts and principles involved
2. Analyze the problem systematically 
3. Evaluate each option carefully
4. Provide your final answer in the format: Answer: <letter>

Think carefully and show your reasoning, then give your definitive answer."""

        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        logging.info("Sending question to LLM...")
        
        # Get LLM response
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer using multiple patterns
        patterns = [
            r'Answer:\s*([A-D])\b',  # Answer: A
            r'Answer:\s*&lt;([A-D])&gt;',  # Answer: &lt;A&gt;  
            r'final answer is\s*([A-D])\b',  # final answer is A
            r'answer is\s*([A-D])\b',  # answer is A
            r'choose\s*([A-D])\b',  # choose A
            r'select\s*([A-D])\b',  # select A
            r'option\s*([A-D])\b',  # option A
            r'letter\s*([A-D])\b',  # letter A
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Look for contextual patterns
        context_patterns = [
            r'\b([A-D])\)\s',  # A) or B) etc
            r'\b([A-D])\s*is\s*(correct|right|the answer)',  # A is correct
            r'correct answer.*?([A-D])\b',  # correct answer ... A
            r'the answer.*?([A-D])\b',  # the answer ... A
        ]
        
        for pattern in context_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Handle tuples from groups
                answer = matches[-1][0].upper() if isinstance(matches[-1], tuple) else matches[-1].upper()
                logging.info(f"Extracted contextual answer: {answer}")
                return answer
        
        # Final fallback - find isolated letters in likely positions
        # Look in the last part of the response where the final answer would be
        last_part = response[-200:]  # Last 200 characters
        letters = re.findall(r'\b([A-D])\b', last_part.upper())
        if letters:
            answer = letters[-1]
            logging.info(f"Fallback answer from end of response: {answer}")
            return answer
        
        # If still nothing, look anywhere in the response
        all_letters = re.findall(r'\b([A-D])\b', response.upper())
        if all_letters:
            answer = all_letters[-1]
            logging.info(f"Final fallback answer: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer from LLM response, defaulting to A")
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"