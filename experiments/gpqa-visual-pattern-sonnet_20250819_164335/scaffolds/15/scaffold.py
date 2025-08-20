import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for safety
    
    try:
        cleaned_input = input_string.strip()
        logging.info(f"Processing scientific question, length: {len(cleaned_input)}")
        
        # Check for timeout before starting
        if time.time() - start_time > timeout:
            logging.error("Timeout before processing")
            return "A"
        
        # Send the question directly to the LLM since it already contains 
        # instructions for step-by-step reasoning and answer format
        response = execute_llm(cleaned_input)
        logging.info(f"Received LLM response, length: {len(response)}")
        
        # Look for the expected answer format: "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Try alternative patterns for extracting the answer
        alternative_patterns = [
            r'final answer.*?([A-D])',
            r'the answer is.*?([A-D])',
            r'I choose.*?([A-D])',
            r'correct answer.*?([A-D])',
            r'answer.*?([A-D])',
            r'\b([A-D])\b(?=\s*$)',  # Single letter at end of response
        ]
        
        for pattern in alternative_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Check timeout before retry
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout, extracting any letter found")
            letters = re.findall(r'\b([A-D])\b', response)
            return letters[-1].upper() if letters else "A"
        
        # If no clear answer format found, try a more direct approach
        logging.warning("No clear answer found in expected format, trying direct question")
        
        direct_prompt = f"""You are an expert scientist. Answer this multiple choice question by selecting A, B, C, or D:

{cleaned_input}

Provide only the letter of your answer."""

        direct_response = execute_llm(direct_prompt)
        
        # Extract any letter A-D from the direct response
        direct_letters = re.findall(r'([A-D])', direct_response.upper())
        if direct_letters:
            answer = direct_letters[0]
            logging.info(f"Direct approach yielded: {answer}")
            return answer
        
        # Final fallback - look for any A, B, C, D in original response
        all_letters = re.findall(r'\b([A-D])\b', response.upper())
        if all_letters:
            answer = all_letters[-1]  # Take the last occurrence
            logging.info(f"Fallback: using last letter found: {answer}")
            return answer
        
        # Ultimate fallback
        logging.error("Could not determine answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception in process_input: {str(e)}")
        return "A"  # Safe fallback

def process_input(input_string: str) -> str:
    return process_input_impl(input_string)

def process_input_impl(input_string: str) -> str:
    start_time = time.time()
    timeout = 115
    
    try:
        cleaned_input = input_string.strip()
        logging.info(f"Processing question, input length: {len(cleaned_input)}")
        
        if time.time() - start_time > timeout:
            return "A"
        
        # Send to LLM - the input already contains step-by-step instructions
        response = execute_llm(cleaned_input)
        logging.info(f"Received response, extracting answer")
        
        # Primary extraction: look for "Answer: X" format
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Secondary: look for common answer patterns
        patterns = [
            r'final answer.*?([A-D])',
            r'answer.*?is.*?([A-D])', 
            r'choose.*?([A-D])',
            r'correct.*?([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Tertiary: any A-D letter, prefer later occurrences
        letters = re.findall(r'\b([A-D])\b', response.upper())
        if letters:
            return letters[-1]
        
        return "A"
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return "A"