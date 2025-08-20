import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before 120s timeout
    
    try:
        logging.info(f"Processing question: {input_string[:200]}...")
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning default answer")
            return 'A'
        
        # Use a system prompt to emphasize scientific expertise
        system_prompt = """You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, and mathematics. Please solve the following multiple choice question with careful step-by-step reasoning. Pay close attention to scientific principles, mathematical calculations, and logical deduction."""
        
        response = execute_llm(input_string, system_prompt)
        
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching after first LLM call")
            # Quick extraction attempt
            answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
            if answer_match:
                return answer_match.group(1).upper()
            return 'A'
        
        # Extract the final answer in the expected format "Answer: X"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback patterns
        answer_patterns = [
            r'(?:the\s+)?answer\s+is\s*([A-D])',
            r'(?:correct\s+)?choice\s+is\s*([A-D])',
            r'option\s+([A-D])',
            r'select\s+([A-D])'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer via pattern: {answer}")
                return answer
        
        # If no clear format found, ask for clarification
        if time.time() - start_time < timeout - 10:  # Only if we have time
            clarification_prompt = f"""Based on your previous analysis, what is your final answer letter (A, B, C, or D)?

Previous response:
{response}

Respond with only the single letter (A, B, C, or D)."""
            
            clarification_response = execute_llm(clarification_prompt).strip().upper()
            
            if clarification_response in ['A', 'B', 'C', 'D']:
                logging.info(f"Got clarified answer: {clarification_response}")
                return clarification_response
            
            # Extract letter from clarification response
            letter_match = re.search(r'([A-D])', clarification_response)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Extracted answer from clarification: {answer}")
                return answer
        
        # Last resort: find the last occurrence of any option letter in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1].upper()
            logging.info(f"Using last letter found: {answer}")
            return answer
        
        logging.warning(f"Could not extract clear answer from response: {response[:300]}...")
        return 'A'  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return 'A'  # Return default answer on error