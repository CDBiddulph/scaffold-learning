import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check time constraint early
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching time limit, returning default answer")
            return "A"
        
        logging.info(f"Processing input: {input_string[:200]}...")
        
        # Create a system prompt to guide the LLM
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and other scientific disciplines. You will be given a multiple choice question with options A, B, C, and D.

Your task is to:
1. Carefully analyze the question and understand what is being asked
2. Apply relevant scientific principles and knowledge
3. Evaluate each option systematically
4. Choose the best answer based on scientific reasoning
5. Always conclude your response with "Answer: <letter>" where <letter> is A, B, C, or D

Be thorough in your scientific reasoning but make sure to clearly state your final answer."""
        
        # Send the input to the LLM
        response = execute_llm(input_string, system_prompt=system_prompt)
        
        logging.info(f"LLM response: {response}")
        
        # Try multiple patterns to extract the answer, ordered by preference
        patterns = [
            r'Answer:\s*([ABCD])',  # Primary format
            r'Answer:\s*&lt;([ABCD])&gt;',  # HTML encoded format
            r'final answer.*?is\s*([ABCD])',
            r'answer is\s*([ABCD])',
            r'correct answer is\s*([ABCD])',
            r'the answer is\s*([ABCD])',
            r'\b([ABCD])\s*is (?:the )?(?:correct|right|best|final) answer',
            r'therefore.*?([ABCD])',
            r'thus.*?([ABCD])',
            r'so.*?([ABCD])',
            r'conclusion.*?([ABCD])',
            r'choose\s*([ABCD])',
            r'select\s*([ABCD])'
        ]
        
        for i, pattern in enumerate(patterns):
            matches = list(re.finditer(pattern, response, re.IGNORECASE | re.DOTALL))
            if matches:
                # Take the last match for this pattern
                answer = matches[-1].group(1).upper()
                logging.info(f"Extracted answer using pattern {i+1} '{pattern}': {answer}")
                if answer in ['A', 'B', 'C', 'D']:
                    return answer
        
        # Final fallback: look for the last occurrence of any option letter in the response
        letters_found = re.findall(r'\b([ABCD])\b', response)
        if letters_found:
            answer = letters_found[-1]
            logging.info(f"Fallback answer: {answer}")
            return answer
        
        # If all else fails, try asking the LLM again with a more direct prompt
        if time.time() - start_time < 90:  # Only if we have time
            logging.warning("First attempt failed, trying simplified prompt")
            simplified_prompt = f"{input_string}\n\nPlease respond with only the letter (A, B, C, or D) of your answer."
            simple_response = execute_llm(simplified_prompt)
            
            letter_match = re.search(r'\b([ABCD])\b', simple_response)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Answer from simplified prompt: {answer}")
                return answer
        
        logging.warning("Could not extract answer from any LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Default fallback