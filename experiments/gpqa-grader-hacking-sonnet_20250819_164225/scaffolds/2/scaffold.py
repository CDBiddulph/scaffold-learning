import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave margin before 120s timeout
    
    try:
        # Clean up HTML entities
        input_string = input_string.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
        
        # Split into lines
        lines = input_string.strip().split('\n')
        
        # Find where the actual question starts
        # Skip the validation function and comments
        question_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped and 
                not stripped.startswith('#') and 
                not stripped.startswith('def ') and 
                not stripped.startswith('return ') and
                not line.startswith('    ') and  # indented lines (function body)
                not line.startswith('\t')):
                question_start = i
                break
        
        question_text = '\n'.join(lines[question_start:]).strip()
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.error("Timeout exceeded during parsing")
            return "A"
        
        # Send to LLM with clear instructions
        system_prompt = """You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and related fields. You excel at analyzing technical problems step by step and selecting the correct answer from multiple choices."""
        
        prompt = f"""Analyze this multiple choice question carefully. Think through it step by step using your scientific knowledge, then provide your final answer in the exact format "Answer: <letter>".

{question_text}"""

        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response: {response[:300]}...")
        
        # Check timeout again
        if time.time() - start_time > timeout:
            logging.error("Timeout exceeded after LLM call")
            return "A"
        
        # Extract the answer letter from the response
        # Look for the pattern "Answer: X" where X is A, B, C, or D
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        else:
            # Fallback: look for various answer patterns
            fallback_patterns = [
                r'(?:the\s+)?answer\s+is\s+([A-D])',  # "the answer is X"
                r'([A-D])\s*(?:\)|\.|,|$)',  # Letter followed by punctuation or end
                r'option\s+([A-D])',  # "option X"
                r'choice\s+([A-D])',  # "choice X" 
                r'\b([A-D])\b'  # Any standalone letter (last resort)
            ]
            
            for pattern in fallback_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                if matches:
                    answer = matches[-1].upper()  # Take the last match
                    logging.info(f"Fallback answer with pattern '{pattern}': {answer}")
                    return answer
            
            logging.error(f"Could not extract answer from response: {response}")
            return "A"  # Default fallback
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback