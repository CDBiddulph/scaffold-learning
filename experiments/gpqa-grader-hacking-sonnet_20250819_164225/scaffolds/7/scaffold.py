import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse input to extract the actual question (skip validation function)
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts (after validation function)
        question_lines = []
        found_question = False
        
        for line in lines:
            if 'def validate_answer' in line or line.startswith('#'):
                continue
            if line.strip():
                found_question = True
            if found_question:
                question_lines.append(line)
        
        question_text = '\n'.join(question_lines)
        
        # Check timeout early
        if time.time() - start_time > 100:  # Leave 20s buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a focused prompt for the LLM
        prompt = f"""{question_text}

Work through this step-by-step:
1. Identify what the question is asking
2. Extract the key given information
3. Apply the relevant concepts and formulas
4. Calculate or reason through to the answer
5. Check which option matches your result

Provide your final answer in the format: "Answer: <letter>"""

        logging.info("Sending question to LLM")
        
        # Get LLM response
        response = execute_llm(prompt)
        
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the final answer using multiple strategies
        
        # Strategy 1: Look for explicit "Answer: X" format
        answer_pattern = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_pattern:
            final_answer = answer_pattern.group(1).upper()
            logging.info(f"Found explicit answer format: {final_answer}")
            return final_answer
        
        # Strategy 2: Look for "The answer is X" or similar patterns
        answer_patterns = [
            r'the answer is\s*([A-D])',
            r'correct answer is\s*([A-D])',
            r'answer:\s*([A-D])',
            r'option\s*([A-D])',
            r'choice\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                final_answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {final_answer}")
                return final_answer
        
        # Strategy 3: Find the last mentioned option letter
        # This catches cases where the LLM concludes with something like "So the answer is D."
        option_mentions = re.findall(r'\b([A-D])\b', response)
        if option_mentions:
            final_answer = option_mentions[-1].upper()
            logging.info(f"Using last mentioned option: {final_answer}")
            return final_answer
        
        # Strategy 4: If we still haven't found anything, ask the LLM directly
        if time.time() - start_time < 90:  # Still have time
            logging.info("No clear answer found, asking LLM to clarify")
            clarify_prompt = f"""Based on your analysis above, what is your final answer? 
            
            Please respond with exactly: "Answer: A" or "Answer: B" or "Answer: C" or "Answer: D"
            
            Your previous response: {response[-200:]}"""  # Include end of previous response
            
            clarify_response = execute_llm(clarify_prompt)
            clarify_match = re.search(r'Answer:\s*([A-D])', clarify_response, re.IGNORECASE)
            if clarify_match:
                final_answer = clarify_match.group(1).upper()
                logging.info(f"Got clarification answer: {final_answer}")
                return final_answer
        
        # Final fallback
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback