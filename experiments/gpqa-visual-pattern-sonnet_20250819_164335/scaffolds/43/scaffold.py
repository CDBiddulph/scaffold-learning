import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 120  # seconds
    
    try:
        # Clean the input - remove any ■ symbols that might indicate correct answers in examples
        question_text = input_string.replace('■', '').strip()
        
        # Extract just the question part before "Think step-by-step"
        question_match = re.search(r'^(.+?)Think step-by-step', question_text, re.DOTALL)
        if question_match:
            question_text = question_match.group(1).strip()
        
        logging.info(f"Processing question: {question_text[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout - 20:
            logging.warning("Approaching timeout early, returning default answer")
            return "A"
        
        # Create a comprehensive prompt for the LLM
        system_prompt = """You are an expert scientist with deep knowledge across all scientific disciplines including physics, chemistry, biology, astronomy, molecular biology, quantum mechanics, organic chemistry, nuclear physics, cell biology, and more. You excel at analyzing complex scientific problems and selecting the correct answers from multiple choice options."""
        
        prompt = f"""Analyze this scientific question carefully and select the best answer:

{question_text}

Think through the problem step by step using your scientific knowledge, then provide your final answer in the exact format: "Answer: X" where X is the letter A, B, C, or D."""
        
        # Check timeout before LLM call
        if time.time() - start_time > timeout - 15:
            logging.warning("Approaching timeout before LLM call, returning default answer")
            return "A"
        
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received (first 300 chars): {response[:300]}...")
        
        # Extract the answer letter using multiple strategies
        answer_patterns = [
            r'Answer:\s*([A-D])',  # Exact format requested
            r'answer\s+is\s+([A-D])',  # Common phrasing
            r'correct\s+answer\s+is\s+([A-D])',  # Alternative phrasing
            r'final\s+answer\s*:?\s*([A-D])',  # Final answer phrasing
            r'\bAnswer\s*([A-D])\b',  # Answer followed by letter
            r'\b([A-D])\)?\s*\.?\s*$',  # Letter at the end of response
        ]
        
        for i, pattern in enumerate(answer_patterns):
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern {i+1} ('{pattern}'): {answer}")
                return answer
        
        # Final fallback - look for any single letter A-D in the last part of the response
        last_part = response[-200:]  # Last 200 characters
        single_letters = re.findall(r'\b([A-D])\b', last_part)
        if single_letters:
            answer = single_letters[-1].upper()  # Take the last one found
            logging.info(f"Extracted fallback answer from end of response: {answer}")
            return answer
        
        # If still no answer found, default to A
        logging.warning("Could not extract any answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe default fallback