import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before the 120s limit
    
    try:
        # Find the content between metadata and the instruction
        metadata_end = input_string.find('</question-metadata>')
        if metadata_end == -1:
            logging.error("Could not find end of metadata")
            return "A"
        
        instruction_start = input_string.find('Think step-by-step')
        if instruction_start == -1:
            logging.error("Could not find instruction start")
            return "A"
        
        # Extract the question content
        question_content = input_string[metadata_end + len('</question-metadata>'):instruction_start].strip()
        
        logging.info(f"Extracted question content length: {len(question_content)}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.error("Timeout reached during parsing")
            return "A"
        
        # Construct the prompt for the LLM
        prompt = f"""You are a scientific expert. Please analyze this multiple choice question carefully and determine the correct answer.

{question_content}

Please think through this step-by-step, showing your reasoning. Then provide your final answer in the exact format "Final Answer: X" where X is the letter (A, B, C, or D) of the correct option."""
        
        # Check timeout before calling LLM
        if time.time() - start_time > timeout:
            logging.error("Timeout reached before LLM call")
            return "A"
            
        # Get the LLM response
        logging.info("Calling LLM for analysis")
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer from the response using multiple patterns
        
        # Pattern 1: "Final Answer: X"
        answer_match = re.search(r'Final Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer (Final Answer pattern): {answer}")
            return answer
        
        # Pattern 2: "Answer: X"
        answer_match = re.search(r'(?:^|\n)Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer (Answer pattern): {answer}")
            return answer
        
        # Pattern 3: "The answer is X"
        answer_match = re.search(r'The answer is\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer (The answer is pattern): {answer}")
            return answer
        
        # Pattern 4: "I choose X" or "I select X"
        answer_match = re.search(r'I (?:choose|select)\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer (I choose pattern): {answer}")
            return answer
        
        # Pattern 5: Look for "option X" or "choice X" near the end
        option_mentions = re.findall(r'(?:option|choice)\s*([A-D])', response, re.IGNORECASE)
        if option_mentions:
            answer = option_mentions[-1].upper()
            logging.info(f"Using last mentioned option: {answer}")
            return answer
        
        # Pattern 6: Look for standalone letters at the end
        # Find all single letters that could be answers
        lines = response.split('\n')
        for line in reversed(lines[-10:]):  # Check last 10 lines
            line_stripped = line.strip()
            if re.match(r'^[A-D]\.?$', line_stripped):
                answer = line_stripped[0].upper()
                logging.info(f"Using standalone letter at end: {answer}")
                return answer
        
        # Pattern 7: Last resort - find any letter mention
        letters_mentioned = re.findall(r'\b([A-D])\b', response)
        if letters_mentioned:
            answer = letters_mentioned[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        # Default fallback
        logging.warning("Could not extract answer from LLM response, using default A")
        logging.warning(f"Response was: {response[:1000]}")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return "A"