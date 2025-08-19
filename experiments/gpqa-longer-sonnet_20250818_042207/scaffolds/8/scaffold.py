import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove any trailing instructions about formatting that appear in examples
        cleaned_input = re.sub(r'\n\s*Think step-by-step.*', '', input_string, flags=re.DOTALL)
        cleaned_input = cleaned_input.strip()
        
        logging.info(f"Processing question: {cleaned_input[:150]}...")
        
        # Create a clear, focused prompt for the LLM
        prompt = f"""{cleaned_input}

Analyze this scientific multiple choice question carefully and select the correct answer. Provide your reasoning and then state your final answer as just the letter: A, B, C, or D"""
        
        # Check timeout before LLM call
        if time.time() - start_time > 90:
            logging.warning("Approaching timeout before LLM call")
            return "A"
        
        # Get response from LLM
        response = execute_llm(prompt)
        logging.info(f"LLM response received: {len(response)} characters")
        
        # Check timeout after LLM call
        if time.time() - start_time > 115:
            logging.warning("Approaching timeout after LLM call")
            return "A"
        
        # Extract the answer letter using multiple strategies
        # Strategy 1: Look for explicit answer patterns
        patterns = [
            r'final answer.*?is.*?([A-D])',
            r'answer.*?is.*?([A-D])', 
            r'answer.*?([A-D])',
            r'Answer:\s*([A-D])',
            r'the correct.*?([A-D])',
            r'choose.*?([A-D])',
            r'select.*?([A-D])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 2: Look for isolated letters in the last few lines
        lines = response.split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            line = line.strip()
            if len(line) <= 10:  # Short lines more likely to contain just the answer
                match = re.search(r'\b([A-D])\b', line)
                if match:
                    answer = match.group(1)
                    logging.info(f"Found answer in short line '{line}': {answer}")
                    return answer
        
        # Strategy 3: Look for the last occurrence of A/B/C/D in the response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1]
            logging.info(f"Using last letter found: {answer}")
            return answer
        
        # Strategy 4: If no clear pattern, try a follow-up prompt
        if time.time() - start_time < 110:
            followup_prompt = f"""Based on your previous analysis, what is your final answer? Respond with only the letter A, B, C, or D."""
            
            followup_response = execute_llm(followup_prompt)
            match = re.search(r'\b([A-D])\b', followup_response)
            if match:
                answer = match.group(1)
                logging.info(f"Got answer from followup: {answer}")
                return answer
        
        logging.warning(f"Could not extract clear answer from response: {response[:200]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback