import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s timeout
    
    try:
        logging.info("Processing academic multiple choice question")
        
        # Check timeout before starting
        if time.time() - start_time > timeout:
            logging.error("Timeout approaching at start")
            return "A"
        
        # Send the complete question to LLM (it already has the proper instructions)
        response = execute_llm(input_string)
        logging.info(f"LLM response received, length: {len(response)} characters")
        
        # Look for all "Answer: <letter>" patterns and take the last one
        # This handles cases where the LLM might mention other options before giving final answer
        answer_matches = re.findall(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_matches:
            answer = answer_matches[-1].upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback patterns in case the LLM doesn't use the exact "Answer:" format
        fallback_patterns = [
            r'final answer is\s*([A-D])',
            r'the answer is\s*([A-D])',
            r'I choose\s*([A-D])',
            r'option\s*([A-D])\s*is\s*correct',
            r'correct answer\s*is\s*([A-D])',
            r'\bcorrect\s*:\s*([A-D])',
            r'therefore\s*([A-D])',
            r'so\s*the\s*answer\s*is\s*([A-D])'
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Extracted answer using fallback pattern '{pattern}': {answer}")
                return answer
        
        # If we still haven't found an answer and have time, ask for clarification
        if time.time() - start_time < timeout - 25:
            logging.warning("No answer pattern found, requesting clarification")
            clarify_prompt = (
                f"You were asked: {input_string[:300]}...\n\n"
                "Please provide only your final answer choice in this exact format: Answer: A\n"
                "(Replace A with B, C, or D as appropriate)"
            )
            
            try:
                clarify_response = execute_llm(clarify_prompt)
                answer_matches = re.findall(r'Answer:\s*([A-D])', clarify_response, re.IGNORECASE)
                if answer_matches:
                    answer = answer_matches[-1].upper()
                    logging.info(f"Extracted answer from clarification: {answer}")
                    return answer
            except Exception as e:
                logging.error(f"Error in clarification request: {e}")
        
        # Last resort: look for any standalone letters that might be the answer
        # But only if they appear near the end of the response
        response_end = response[-200:]  # Look at last 200 characters
        standalone_matches = re.findall(r'\b([A-D])\b', response_end)
        if standalone_matches:
            answer = standalone_matches[-1].upper()
            logging.info(f"Using standalone letter from response end: {answer}")
            return answer
        
        # If all else fails, return A as default
        logging.error("Failed to extract any answer using all methods")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {str(e)}")
        return "A"