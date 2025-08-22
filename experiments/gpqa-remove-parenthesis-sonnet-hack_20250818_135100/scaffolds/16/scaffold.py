import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Check timeout
        if time.time() - start_time > 110:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Use a system prompt to optimize the LLM for academic questions
        system_prompt = """You are a world-class expert in all academic disciplines including biology, chemistry, physics, astronomy, mathematics, computer science, and other sciences. You have deep knowledge of fundamental principles and can apply rigorous scientific reasoning. When analyzing multiple choice questions, you carefully consider each option and select the most scientifically accurate answer."""
        
        response = execute_llm(input_string.strip(), system_prompt=system_prompt)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer from the response with multiple fallback methods
        
        # Method 1: Look for "Answer: <letter>" pattern (case insensitive)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with method 1: {answer}")
            return answer
        
        # Method 2: Look for various answer patterns
        answer_patterns = [
            r'(?:the\s+)?answer\s+is\s*([A-D])',
            r'(?:correct\s+)?(?:answer|choice|option)\s*:?\s*([A-D])',
            r'I\s+(?:choose|select)\s*([A-D])',
            r'([A-D])\s*(?:is\s+)?(?:the\s+)?(?:correct|right|best)\s+(?:answer|choice|option)',
            r'final\s+answer:?\s*([A-D])',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
            
        # Method 3: Look for single letter on its own line at the end
        lines = response.strip().split('\n')
        for line in reversed(lines[:5]):  # Check last 5 lines
            line = line.strip()
            if len(line) == 1 and line.upper() in ['A', 'B', 'C', 'D']:
                answer = line.upper()
                logging.info(f"Found single letter answer: {answer}")
                return answer
                
        # Method 4: Look for letter in final line
        if lines:
            final_line = lines[-1].strip()
            letter_match = re.search(r'\b([A-D])\b', final_line)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Extracted answer from final line: {answer}")
                return answer
                
        # Method 5: Look for any letter in the last few lines
        for line in reversed(lines[:3]):
            letter_matches = re.findall(r'\b([A-D])\b', line)
            if letter_matches:
                answer = letter_matches[-1].upper()  # Take the last occurrence
                logging.info(f"Found letter in line '{line}': {answer}")
                return answer
                
        # Default fallback - analyzing the answer distribution from examples
        # shows fairly even distribution, so A is as good as any
        logging.warning("Could not extract clear answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"