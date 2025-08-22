import re
import logging
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    question = input_string.strip()
    
    # System prompt to establish the LLM's role as a scientific expert
    system_prompt = """You are a world-class scientific expert with deep knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering. You excel at solving complex multiple-choice questions by breaking them down step by step."""
    
    # Main prompt asking for structured reasoning
    prompt = f"""{question}

Please solve this step by step:
1. First, identify the key scientific concepts involved
2. Apply relevant principles, equations, or knowledge
3. Work through any necessary calculations or logical reasoning
4. Eliminate incorrect options where possible
5. Conclude with your final answer

Provide your final answer in the exact format: "Answer: <letter>" where <letter> is A, B, C, or D."""
    
    try:
        # Check timeout buffer
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Primary extraction: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer using primary pattern: {final_answer}")
            return final_answer
        
        # Secondary patterns for answer extraction
        patterns = [
            r'final answer is\s*([A-D])',
            r'answer is\s*([A-D])',
            r'choose\s*([A-D])',
            r'select\s*([A-D])',
            r'correct answer\s*is\s*([A-D])',
            r'therefore.*?([A-D])\)',
            r'thus.*?([A-D])\)',
            r'so.*?([A-D])\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                final_answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {final_answer}")
                return final_answer
        
        # Look for the last mentioned option in the response
        all_options = re.findall(r'\b([A-D])\)', response)
        if all_options:
            final_answer = all_options[-1].upper()
            logging.info(f"Extracted answer from last option mention: {final_answer}")
            return final_answer
        
        # Last resort: any standalone letter A-D in the final part of response
        response_end = response[-500:]  # Look at last 500 characters
        any_letter = re.findall(r'\b([A-D])\b', response_end)
        if any_letter:
            final_answer = any_letter[-1].upper()
            logging.info(f"Extracted answer from standalone letter: {final_answer}")
            return final_answer
            
        # If all else fails, try to get a direct answer with a follow-up
        if time.time() - start_time < 90:  # Still have time for follow-up
            follow_up = f"""Based on your analysis above, what is your final answer? Respond with just the letter A, B, C, or D."""
            follow_response = execute_llm(follow_up)
            
            direct_answer = re.search(r'\b([A-D])\b', follow_response)
            if direct_answer:
                final_answer = direct_answer.group(1).upper()
                logging.info(f"Extracted answer from follow-up: {final_answer}")
                return final_answer
        
        logging.warning(f"Could not extract clear answer from response. Response start: {response[:200]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Safe fallback