import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 110  # Leave buffer before the 120s timeout
    
    logging.info("Processing multiple choice question with LLM")
    
    # System prompt to help the LLM focus on scientific accuracy
    system_prompt = """You are an expert in multiple scientific disciplines including physics, chemistry, astronomy, biology, and mathematics. You will be given multiple choice questions that require deep technical knowledge. 

Please read each question carefully, think through the problem step by step using your scientific knowledge, and provide a clear final answer in the exact format requested."""

    try:
        # Check if we're approaching timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response length: {len(response)} characters")
        
        # Check timeout again after LLM call
        if time.time() - start_time > timeout:
            logging.warning("Timeout reached after LLM call, proceeding with answer extraction")
        
        # Extract the answer letter using multiple strategies
        
        # Strategy 1: Look for "Answer: <letter>" pattern (most common)
        answer_match = re.search(r'Answer:\s*<?([A-D])>?', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for HTML entity format "Answer: &lt;letter&gt;"
        answer_match = re.search(r'Answer:\s*&lt;([A-D])&gt;', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from HTML entity pattern: {answer}")
            return answer
        
        # Strategy 3: Look for standalone letters at end of lines
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        for line in reversed(lines):
            if line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone answer letter: {line}")
                return line
            # Check if line ends with a letter
            if re.search(r'\b([A-D])\s*$', line):
                answer = re.search(r'\b([A-D])\s*$', line).group(1).upper()
                logging.info(f"Found answer letter at end of line: {answer}")
                return answer
        
        # Strategy 4: Look for common answer patterns
        answer_patterns = [
            r'(?:answer|choice|option)\s+is\s+([A-D])',
            r'therefore[,\s]+([A-D])',
            r'thus[,\s]+([A-D])',
            r'so[,\s]+the\s+answer\s+is\s+([A-D])',
            r'the\s+correct\s+answer\s+is\s+([A-D])',
            r'([A-D])\s+is\s+correct'
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer using pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 5: Final fallback - any isolated letters (take last occurrence)
        single_letters = re.findall(r'\b([A-D])\b', response)
        if single_letters:
            answer = single_letters[-1]
            logging.info(f"Found single letter answer (last occurrence): {answer}")
            return answer
        
        logging.error(f"Could not extract answer from response: {response[:500]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        elapsed = time.time() - start_time
        logging.error(f"Error processing question after {elapsed:.2f}s: {e}")
        return "A"  # Default fallback