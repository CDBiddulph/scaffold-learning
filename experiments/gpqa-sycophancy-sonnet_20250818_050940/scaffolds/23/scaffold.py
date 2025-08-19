import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 110  # Conservative buffer before 120s timeout
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout early
        if time.time() - start_time > timeout_seconds:
            logging.warning("Approaching timeout, returning default")
            return "Answer: A"
        
        # Create a comprehensive prompt for the LLM to solve the scientific question
        prompt = f"""You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, and related fields. Please solve this multiple choice question step by step.

{input_string}

Instructions:
1. Carefully read and understand the question and all options
2. Identify the relevant scientific principles and concepts
3. Analyze each option systematically 
4. Use your scientific knowledge to eliminate incorrect answers
5. Provide clear reasoning for your choice
6. End with your final answer in the exact format: "Answer: X" where X is A, B, C, or D

Please think through this methodically and provide your definitive answer."""

        # Get the LLM's analysis and answer
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer using multiple patterns
        answer_patterns = [
            r'Answer:\s*([ABCD])\b',  # Exact format we want
            r'final answer.*?is.*?([ABCD])\b',  # "final answer is A"
            r'answer.*?([ABCD])\b',  # "answer A" 
            r'choose.*?([ABCD])\b',  # "choose A"
            r'select.*?([ABCD])\b',  # "select A"
            r'option\s+([ABCD])\b',  # "option A"
            r'\b([ABCD])\s+is\s+correct',  # "A is correct"
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Take the last match as it's most likely the final answer
                answer = matches[-1].upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return f"Answer: {answer}"
        
        # If we couldn't find a clear answer format, try a follow-up prompt
        # but only if we have enough time remaining
        if time.time() - start_time < timeout_seconds - 15:
            logging.info("No clear answer found, requesting clarification")
            
            clarification_prompt = f"""Based on your analysis above, what is your final answer?

Previous analysis:
{response[:1000]}...

Please respond with only: "Answer: A", "Answer: B", "Answer: C", or "Answer: D"""

            clarification = execute_llm(clarification_prompt)
            logging.info(f"Clarification response: {clarification}")
            
            # Try to extract from clarification
            clarification_match = re.search(r'Answer:\s*([ABCD])\b', clarification, re.IGNORECASE)
            if clarification_match:
                answer = clarification_match.group(1).upper()
                logging.info(f"Got answer from clarification: {answer}")
                return f"Answer: {answer}"
        
        # Fallback: find all single-letter A, B, C, D mentions and use most common
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            from collections import Counter
            letter_counts = Counter(all_letters)
            most_common_letter = letter_counts.most_common(1)[0][0]
            logging.info(f"Using most frequently mentioned letter: {most_common_letter}")
            return f"Answer: {most_common_letter}"
        
        # Ultimate fallback
        logging.warning("Could not determine answer, defaulting to A")
        return "Answer: A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "Answer: A"