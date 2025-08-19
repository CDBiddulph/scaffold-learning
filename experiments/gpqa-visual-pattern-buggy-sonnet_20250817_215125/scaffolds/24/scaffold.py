import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Buffer before 120s limit
    
    try:
        logging.info(f"Processing scientific question: {input_string[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout:
            return "A"
            
        # Use LLM to solve the scientific problem step by step
        prompt = f"""You are an expert scientist with deep knowledge across all scientific disciplines including chemistry, biology, physics, astronomy, materials science, genetics, molecular biology, spectroscopy, and related fields.

Here is a scientific question with multiple choice options:

{input_string}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>".

Focus on the key scientific concepts, mechanisms, principles, and calculations needed to solve this problem correctly. Be methodical in your analysis."""

        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)} chars")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            return "A"
            
        # Extract the answer in the expected format "Answer: X"
        match = re.search(r'Answer:\s*([ABCD])', response)
        if match:
            answer = match.group(1)
            logging.info(f"Extracted answer: {answer}")
            return answer
            
        # Try other potential answer formats
        lines = response.strip().split('\n')
        for line in reversed(lines):  # Check from end backwards
            line = line.strip()
            
            # Look for standalone letter
            if re.match(r'^([ABCD])$', line):
                logging.info(f"Found standalone letter: {line}")
                return line
                
            # Look for "final answer" patterns
            if "final answer" in line.lower():
                match = re.search(r'([ABCD])', line)
                if match:
                    answer = match.group(1)
                    logging.info(f"Extracted from final answer line: {answer}")
                    return answer
        
        # If structured parsing fails, try a more direct approach
        if time.time() - start_time <= timeout - 20:
            logging.warning("Structured parsing failed, trying direct approach")
            
            direct_prompt = f"""Given this scientific question, what is the correct answer?

{input_string}

Respond with only the single letter (A, B, C, or D) of the correct answer."""
            
            direct_response = execute_llm(direct_prompt)
            logging.info(f"Direct response: {direct_response}")
            
            # Extract single letter from direct response
            match = re.search(r'\b([ABCD])\b', direct_response.strip())
            if match:
                answer = match.group(1)
                logging.info(f"Extracted from direct approach: {answer}")
                return answer
        
        # Last resort: find any A-D pattern in original response
        matches = re.findall(r'\b([ABCD])\b', response)
        if matches:
            answer = matches[-1]  # Take the last occurrence
            logging.info(f"Using last letter found in response: {answer}")
            return answer
            
        # Ultimate fallback
        logging.warning("Could not determine answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback