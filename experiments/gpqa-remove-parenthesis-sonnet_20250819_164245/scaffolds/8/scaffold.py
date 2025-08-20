import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout_seconds = 115  # Leave buffer before 120s timeout
    
    try:
        input_text = input_string.strip()
        
        # Remove the instruction about thinking step-by-step if present
        if "Think step-by-step" in input_text:
            input_text = input_text.split("Think step-by-step")[0].strip()
        
        logging.info(f"Processing scientific question: {input_text[:100]}...")
        
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logging.error("Approaching timeout")
            return "A"
        
        # Create system prompt to establish expertise
        system_prompt = """You are an expert scientist with deep knowledge across all scientific disciplines including chemistry, physics, biology, astronomy, mathematics, microbiology, genetics, and engineering. You excel at analyzing complex scientific problems and selecting the correct answer from multiple choices."""
        
        # Create main prompt with clear instructions
        prompt = f"""{input_text}

Please solve this scientific question step-by-step:

1. Identify the key scientific concepts and principles involved
2. Analyze each answer choice systematically  
3. Apply your scientific knowledge to evaluate the options
4. Use logical reasoning to eliminate incorrect answers
5. Select the best answer based on scientific evidence

Provide your final answer in this exact format: Answer: <letter>"""

        # Execute LLM
        response = execute_llm(prompt, system_prompt)
        logging.info(f"Received LLM response ({len(response)} chars)")
        
        # Extract answer using multiple patterns for robustness
        answer_patterns = [
            r'Answer:\s*([A-D])',           # Answer: A
            r'answer\s*is\s*([A-D])',      # answer is B  
            r'correct\s*answer\s*is\s*([A-D])',  # correct answer is C
            r'final\s*answer[:\s]*([A-D])',      # final answer: D
            r'choose\s*([A-D])',           # choose A
            r'select\s*([A-D])'            # select B
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                return answer
        
        # Fallback: find all isolated A/B/C/D letters and take the last one
        isolated_letters = re.findall(r'\b([A-D])\b', response)
        if isolated_letters:
            answer = isolated_letters[-1].upper()
            logging.info(f"Using fallback - last letter found: {answer}")
            return answer
        
        # Ultimate fallback
        logging.warning("Could not extract any answer from response")
        return "A"
        
    except Exception as e:
        logging.error(f"Exception occurred: {str(e)}")
        return "A"  # Safe default