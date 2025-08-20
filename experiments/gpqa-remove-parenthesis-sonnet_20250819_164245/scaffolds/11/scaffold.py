import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Timeout safety check
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout")
            return "A"
            
        system_prompt = """You are a world-class scientific expert with comprehensive knowledge across physics, chemistry, biology, astronomy, mathematics, and engineering. Analyze the question carefully and select the most accurate answer. Please follow any formatting instructions provided."""
        
        logging.info("Calling LLM for scientific question")
        response = execute_llm(input_string, system_prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Primary strategy: Look for "Answer: X" format (most questions request this)
        match = re.search(r'Answer:\s*<?([A-D])>?', response, re.IGNORECASE)
        if match:
            answer = match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' format: {answer}")
            return answer
            
        # Secondary strategies for cases where format isn't followed exactly
        
        # Look for definitive answer statements
        definitive_patterns = [
            r'(?:the correct answer is|correct answer is|final answer is)\s+([A-D])\b',
            r'(?:answer is|the answer is)\s+([A-D])\b',
            r'(?:I choose|I select)\s+([A-D])\b',
            r'([A-D])\s+is\s+(?:correct|right|the correct answer)'
        ]
        
        for pattern in definitive_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer via definitive pattern: {answer}")
                return answer
        
        # Look for single letter at end of response
        end_match = re.search(r'\b([A-D])\b\s*$', response.strip())
        if end_match:
            answer = end_match.group(1).upper()
            logging.info(f"Found answer at end: {answer}")
            return answer
        
        # Fallback: take last letter mentioned
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Fallback answer (last letter): {answer}")
            return answer
        
        # Ultimate fallback
        logging.error("No answer found in response")
        logging.error(f"Response sample: {response[:200]}...")
        return "A"
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return "A"