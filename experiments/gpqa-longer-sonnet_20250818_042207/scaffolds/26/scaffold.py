import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Check timeout early
        if time.time() - start_time > 100:  # Leave buffer before 120s timeout
            logging.warning("Approaching timeout, returning early")
            return "A"
        
        system_prompt = """You are an expert scientist with deep knowledge across chemistry, physics, biology, astronomy, mathematics, and other technical fields. 

You will analyze a multiple choice question step-by-step. Please:
1. Read the question and all options carefully
2. Think through the problem systematically 
3. Consider the scientific principles involved
4. Evaluate each option against your reasoning
5. Provide your final answer in the exact format: "Answer: X" where X is A, B, C, or D

Be thorough in your analysis but concise in your explanation."""
        
        # Send the question to the LLM
        response = execute_llm(input_string, system_prompt=system_prompt)
        logging.info(f"LLM response length: {len(response)} chars")
        logging.info(f"Response preview: {response[:200]}...")
        
        # Multiple strategies to extract the answer
        
        # Strategy 1: Look for exact "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with exact format: {answer}")
            return answer
        
        # Strategy 2: Look for other common answer patterns
        patterns = [
            r'the\s+answer\s+is\s+([ABCD])',
            r'correct\s+answer\s+is\s+([ABCD])',
            r'final\s+answer\s*:\s*([ABCD])',
            r'answer\s*:\s*([ABCD])',
            r'option\s+([ABCD])\s+is\s+correct',
            r'([ABCD])\s+is\s+the\s+correct',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look at the end of the response for any answer format
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        if lines:
            last_line = lines[-1]
            # Check if last line contains an answer
            letter_match = re.search(r'\b([ABCD])\b', last_line)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Found answer in last line: {answer}")
                return answer
        
        # Strategy 4: Look for any clear statement about the answer in the last few lines
        for line in reversed(lines[-3:]):  # Check last 3 lines
            if any(word in line.lower() for word in ['answer', 'correct', 'option']):
                letter_match = re.search(r'\b([ABCD])\b', line)
                if letter_match:
                    answer = letter_match.group(1).upper()
                    logging.info(f"Found answer in context line: {answer}")
                    return answer
        
        # Strategy 5: Count letter frequencies and pick the most common
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            # Take the last mentioned letter as it's likely the final answer
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter as fallback: {answer}")
            return answer
        
        # If all else fails, try asking the LLM again more directly
        if time.time() - start_time < 90:  # Still have time for retry
            logging.info("No clear answer found, trying direct follow-up")
            followup_prompt = f"Based on your previous analysis, what is your final answer? Please respond with exactly 'Answer: A', 'Answer: B', 'Answer: C', or 'Answer: D'."
            
            followup_response = execute_llm(followup_prompt)
            direct_match = re.search(r'Answer:\s*([ABCD])', followup_response, re.IGNORECASE)
            if direct_match:
                answer = direct_match.group(1).upper()
                logging.info(f"Found answer in followup: {answer}")
                return answer
        
        logging.warning("Could not extract answer from any strategy, defaulting to A")
        logging.warning(f"Full response was: {response}")
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        logging.error(f"Input was: {input_string[:200]}...")
        return "A"