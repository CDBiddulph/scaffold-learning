import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s limit
    
    try:
        question_text = input_string.strip()
        logging.info("Processing scientific multiple choice question")
        
        # First attempt: Comprehensive analysis
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and related fields. Please analyze this multiple choice question step-by-step.

{question_text}

Think through the relevant scientific principles carefully, then provide your final answer in this exact format: "Answer: X" where X is A, B, C, or D."""
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        response = execute_llm(prompt)
        logging.info(f"Received response of length {len(response)}")
        
        # Extract answer using multiple patterns
        patterns = [
            r"Answer:\s*([ABCD])",  # Exact format requested
            r"final answer is\s*([ABCD])",
            r"correct answer is\s*([ABCD])",
            r"the answer is\s*([ABCD])",
            r"choose\s*([ABCD])",
            r"option\s*([ABCD])\b",
            r"\b([ABCD])\s*is\s*correct",
            r"([ABCD])\)",  # Match "A)", "B)", etc.
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer '{answer}' using pattern: {pattern}")
                return answer
        
        # If no clear answer format, try a direct approach
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default")
            return "A"
        
        direct_prompt = f"""Given this scientific question, what is the single correct answer? 

{question_text}

Respond with only the letter: A, B, C, or D."""
        
        direct_response = execute_llm(direct_prompt).strip()
        logging.info(f"Direct response: '{direct_response}'")
        
        # Extract single letter from direct response
        single_letter = re.search(r"^([ABCD])$", direct_response.strip(), re.IGNORECASE)
        if single_letter:
            answer = single_letter.group(1).upper()
            logging.info(f"Got clean single letter: {answer}")
            return answer
        
        # Look for any letter in the direct response
        any_letter = re.search(r"([ABCD])", direct_response, re.IGNORECASE)
        if any_letter:
            answer = any_letter.group(1).upper()
            logging.info(f"Extracted letter from direct response: {answer}")
            return answer
        
        # Final fallback: look for letters in original response
        all_letters = re.findall(r"\b([ABCD])\b", response, re.IGNORECASE)
        if all_letters:
            # Count frequency and take most common, or last if tied
            from collections import Counter
            letter_counts = Counter(letter.upper() for letter in all_letters)
            answer = letter_counts.most_common(1)[0][0]
            logging.info(f"Using most frequent letter: {answer}")
            return answer
        
        logging.error("Could not extract any answer letter")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        return "A"  # Safe fallback