import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave some buffer before the 120s timeout
    
    try:
        # Split by the "Think step-by-step" instruction to separate question from instruction
        parts = input_string.split("Think step-by-step to explain your reasoning, then write your final answer in the format \"Answer: <letter>\"")
        question_part = parts[0].strip()
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default answer")
            return "A"
        
        # Create a focused prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across chemistry, physics, astronomy, biology, mathematics, and related fields.

Analyze this multiple choice question carefully and select the correct answer:

{question_part}

Provide your reasoning step-by-step, then conclude with your final answer in the format "Answer: X" where X is A, B, C, or D."""
        
        # Check timeout before calling LLM
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching before LLM call, returning default answer")
            return "A"
        
        # Get response from LLM
        logging.info("Sending question to LLM for analysis")
        response = execute_llm(prompt)
        logging.info(f"LLM response received: {response[:200]}...")
        
        # Extract answer from response using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using explicit pattern: {answer}")
            return answer
        
        # Strategy 2: Look for "the answer is X" patterns
        answer_match = re.search(r'(?:the\s+answer\s+is|answer\s+is)\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer using 'answer is' pattern: {answer}")
            return answer
        
        # Strategy 3: Look for final conclusion patterns
        for pattern in [r'(?:therefore|thus|so|conclude|final answer).*?([ABCD])', 
                       r'(?:correct\s+(?:answer|choice|option))\s*(?:is\s*)?([ABCD])',
                       r'(?:I\s+(?:choose|select|pick))\s*([ABCD])']:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 4: Look for standalone letter at the end of response
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        for line in reversed(lines):
            if re.match(r'^[ABCD]$', line):
                answer = line.upper()
                logging.info(f"Found standalone answer letter: {answer}")
                return answer
        
        # Strategy 5: Last resort - look for any mention of letters in final paragraph
        paragraphs = response.split('\n\n')
        if paragraphs:
            last_para = paragraphs[-1]
            letter_matches = re.findall(r'([ABCD])', last_para)
            if letter_matches:
                answer = letter_matches[-1].upper()
                logging.info(f"Found answer in final paragraph: {answer}")
                return answer
        
        # If all strategies fail, log the response and return default
        logging.warning(f"Could not extract answer from LLM response. Full response: {response}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Default fallback