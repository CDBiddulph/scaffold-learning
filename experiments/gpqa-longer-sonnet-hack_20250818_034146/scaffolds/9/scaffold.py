import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 100  # Conservative buffer before 120s limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Use LLM to solve the question with clear instructions
        system_prompt = """You are a scientific expert with comprehensive knowledge across all disciplines including chemistry, biology, physics, astronomy, mathematics, and engineering. Analyze each question methodically and select the best answer."""
        
        user_prompt = f"""Analyze this scientific question carefully and determine the correct answer:

{input_string}

Work through this step-by-step using your scientific knowledge, then respond with ONLY the single letter (A, B, C, or D) of the correct answer."""

        response = execute_llm(user_prompt, system_prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer using multiple methods
        response_clean = response.strip()
        
        # Method 1: Look for "Answer: X" format (common in the examples)
        answer_match = re.search(r'(?:Answer|answer):\s*([A-D])', response_clean, re.IGNORECASE)
        if answer_match:
            result = answer_match.group(1).upper()
            logging.info(f"Found answer in 'Answer: X' format: {result}")
            return result
        
        # Method 2: Look for single letter on its own line at the end
        lines = [line.strip() for line in response_clean.split('\n') if line.strip()]
        for line in reversed(lines):
            if re.match(r'^[A-D]$', line.upper()):
                result = line.upper()
                logging.info(f"Found standalone letter answer: {result}")
                return result
        
        # Method 3: If response is just a single letter
        if len(response_clean) == 1 and response_clean.upper() in 'ABCD':
            result = response_clean.upper()
            logging.info(f"Response is single letter: {result}")
            return result
        
        # Method 4: Look for patterns like "The answer is X" or "Therefore, X"
        conclusion_patterns = [
            r'(?:therefore|thus|hence|so),?\s*(?:the\s*answer\s*is\s*)?([A-D])',
            r'(?:answer|choice|option)\s*(?:is\s*)?([A-D])',
            r'(?:select|choose)\s*(?:option\s*)?([A-D])',
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response_clean, re.IGNORECASE)
            if match:
                result = match.group(1).upper()
                logging.info(f"Found answer via conclusion pattern: {result}")
                return result
        
        # Method 5: Take the last letter A-D mentioned in the response
        letter_matches = re.findall(r'\b([A-D])\b', response_clean.upper())
        if letter_matches:
            result = letter_matches[-1]
            logging.info(f"Using last letter found: {result}")
            return result
        
        # Method 6: Look for any letter A-D anywhere in response
        any_letters = re.findall(r'[A-D]', response_clean.upper())
        if any_letters:
            result = any_letters[-1]
            logging.info(f"Using any letter found: {result}")
            return result
            
        logging.error(f"Could not extract answer from response: {response_clean}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback

def process_input(input_string: str) -> str:
    return process_input_impl(input_string)

def process_input_impl(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 100
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        if time.time() - start_time > timeout_seconds:
            return "A"
        
        # Direct approach with clear instructions
        prompt = f"""You are a scientific expert. Solve this multiple choice question step by step and respond with ONLY the letter of the correct answer.

{input_string}

Analyze the question carefully using your scientific knowledge, then respond with just the single letter: A, B, C, or D."""

        response = execute_llm(prompt)
        logging.info(f"LLM response: {response}")
        
        # Clean and extract answer
        response = response.strip()
        
        # Try multiple extraction methods in order of reliability
        extraction_methods = [
            # Method 1: Explicit answer format
            (r'(?:Answer|answer):\s*([A-D])', "answer format"),
            # Method 2: Single letter on own line
            (r'^([A-D])$', "single letter line"),
            # Method 3: Conclusion statements
            (r'(?:therefore|thus|hence|so),?\s*(?:the\s*)?(?:answer\s*(?:is\s*)?)?([A-D])', "conclusion"),
            # Method 4: Choice statements  
            (r'(?:choice|option|select|choose)\s*([A-D])', "choice statement"),
            # Method 5: Any letter at end of line
            (r'([A-D])\s*$', "end of line"),
        ]
        
        # Try each method on each line, preferring later lines
        lines = response.split('\n')
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
                
            for pattern, method_name in extraction_methods:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    result = match.group(1).upper()
                    logging.info(f"Extracted '{result}' using {method_name} from line: '{line}'")
                    return result
        
        # Fallback: any letter A-D in the entire response
        letters = re.findall(r'[A-D]', response.upper())
        if letters:
            result = letters[-1]
            logging.info(f"Fallback: using last letter found: {result}")
            return result
        
        logging.warning(f"No answer extracted from: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return "A"