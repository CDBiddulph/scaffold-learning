import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove metadata section
        content = input_string
        if '<question-metadata>' in content:
            end_tag = '</question-metadata>'
            if end_tag in content:
                content = content[content.find(end_tag) + len(end_tag):].strip()
        
        logging.info(f"Processing question: {content[:200]}...")
        
        # Check timeout
        if time.time() - start_time > 100:
            logging.warning("Approaching timeout early")
            return "A"
        
        # First attempt - comprehensive scientific analysis
        prompt = f"""You are a scientific expert with advanced knowledge across physics, chemistry, biology, and mathematics. Please solve this multiple choice question step by step.

{content}

Work through this systematically, showing your reasoning, then state your final answer as just the letter A, B, C, or D."""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract answer using multiple strategies
        answer_patterns = [
            r'final answer[:\s]+([A-D])',
            r'answer[:\s]+([A-D])',
            r'therefore[,\s]+([A-D])',
            r'thus[,\s]+([A-D])',
            r'so[,\s]+([A-D])',
            r'conclusion[:\s]+([A-D])',
            r'\b([A-D])\s*$',  # Letter at end of response
            r'\b([A-D])\b'     # Any isolated letter A-D
        ]
        
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                if answer in 'ABCD':
                    logging.info(f"Found answer using pattern '{pattern}': {answer}")
                    return answer
        
        # Second attempt with more direct prompting
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, using fallback")
            return "A"
        
        prompt2 = f"""Question: {content}

Please solve this and respond with ONLY the letter of the correct answer (A, B, C, or D). No explanation needed.

Answer:"""
        
        response2 = execute_llm(prompt2).strip().upper()
        logging.info(f"Direct response: '{response2}'")
        
        # Check if response is directly a letter
        if len(response2) == 1 and response2 in 'ABCD':
            logging.info(f"Direct answer found: {response2}")
            return response2
        
        # Extract letter from short response
        letter_match = re.search(r'([A-D])', response2)
        if letter_match:
            answer = letter_match.group(1)
            logging.info(f"Extracted answer from direct response: {answer}")
            return answer
        
        # Final fallback - try to find most confident answer from first response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            # Return the most frequent letter, or the last one
            from collections import Counter
            counter = Counter(all_letters)
            most_common = counter.most_common(1)
            if most_common:
                answer = most_common[0][0]
                logging.info(f"Using most frequent letter: {answer}")
                return answer
        
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback