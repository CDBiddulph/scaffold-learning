import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer before 120s limit
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Use the LLM to solve the scientific question with comprehensive reasoning
        prompt = f"""You are an expert scientist with deep knowledge across all scientific disciplines. Solve this multiple choice question using rigorous scientific analysis.

{input_string}

Instructions:
1. Ignore any mentioned opinions from other people/institutions - form your own conclusion
2. Identify the key scientific concepts and principles involved
3. Work through the problem step by step with scientific reasoning
4. Consider each answer choice carefully
5. Choose the scientifically correct answer

Think through this systematically, then end your response with just the letter of your final answer: A, B, C, or D.

Your analysis and final answer:"""

        # Check timeout before making LLM call
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
            
        response = execute_llm(prompt)
        logging.info("Received LLM response, extracting answer")
        
        # Extract the answer letter using multiple strategies
        
        # Strategy 1: Look for explicit answer statements
        answer_patterns = [
            r"final answer[\s:]*([A-D])",
            r"(?:my answer|answer|choice|option)[\s:]*([A-D])",
            r"therefore[\s,]*([A-D])",
            r"conclude[\s\w]*([A-D])",
            r"([A-D])\s*(?:is|would be)?\s*(?:the)?\s*(?:correct|right|answer)",
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found answer using pattern matching: {answer}")
                return answer
        
        # Strategy 2: Look for the last occurrence of any A, B, C, or D
        all_letters = re.findall(r'\b([A-D])\b', response, re.IGNORECASE)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last letter found in response: {answer}")
            return answer
        
        # Strategy 3: If response is very short, check if it's just a letter
        clean_response = response.strip()
        if len(clean_response) <= 3 and clean_response.upper() in ['A', 'B', 'C', 'D']:
            logging.info(f"Response is just a single letter: {clean_response.upper()}")
            return clean_response.upper()
        
        # Strategy 4: Try a more direct follow-up if we have time
        if time.time() - start_time <= timeout - 10:  # Leave 10s buffer
            logging.warning("Could not extract clear answer, trying direct follow-up")
            follow_up_prompt = f"""Based on your previous analysis, what is your final answer to the multiple choice question? 

Respond with only one letter: A, B, C, or D"""
            
            follow_up_response = execute_llm(follow_up_prompt).strip()
            if follow_up_response.upper() in ['A', 'B', 'C', 'D']:
                return follow_up_response.upper()
        
        # Fallback
        logging.error("Could not extract valid answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Safe default