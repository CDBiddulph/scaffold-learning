import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer from the 120 second limit
    
    try:
        # Clean the input
        input_text = input_string.strip()
        
        # Check timeout early
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached, returning default answer")
            return "A"
        
        logging.info(f"Processing question: {input_text[:200]}...")
        
        # System prompt to guide the LLM
        system_prompt = """You are a scientific expert with deep knowledge across multiple disciplines including physics, chemistry, biology, astronomy, and mathematics. You excel at solving complex multiple choice questions by breaking them down step by step."""
        
        # Construct prompt for LLM
        prompt = f"""Analyze this scientific multiple choice question and determine the correct answer.

{input_text}

Please think step-by-step, show your reasoning clearly, and then state your final answer as "Answer: X" where X is A, B, C, or D."""

        # Get response from LLM
        response = execute_llm(prompt, system_prompt=system_prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer from the response
        # Look for "Answer: X" pattern (most specific)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer: X' pattern: {answer}")
            return answer
        
        # Fallback: look for other common patterns
        patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([ABCD])',
            r'(?:therefore|thus|so),?\s*(?:the\s+answer\s+is\s+)?([ABCD])',
            r'final\s+answer:?\s*([ABCD])',
            r'choice\s+([ABCD])',
            r'option\s+([ABCD])',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer from pattern {i}: {answer}")
                return answer
        
        # Look at the end of the response for isolated letters
        # Split into sentences and check the last few
        sentences = re.split(r'[.!?]+', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            letters = re.findall(r'\b([ABCD])\b', sentence.strip())
            if letters:
                answer = letters[-1]
                logging.info(f"Extracted answer from end of response: {answer}")
                return answer
        
        # If no answer found, return A as default
        logging.warning("Could not extract answer from LLM response, returning default A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback