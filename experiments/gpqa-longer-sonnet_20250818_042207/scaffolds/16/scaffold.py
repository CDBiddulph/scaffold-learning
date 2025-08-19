import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    try:
        logging.info("Processing scientific multiple choice question")
        
        # The input already contains the full question and instruction format
        response = execute_llm(input_string.strip())
        logging.info("Received LLM response")
        
        # Primary extraction: Look for the exact format "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback patterns for different answer formats
        fallback_patterns = [
            r'(?:the\s+)?answer\s+is\s+([ABCD])',
            r'final\s+answer[:\s]*([ABCD])', 
            r'therefore[,\s]*(?:the\s+answer\s+is\s+)?([ABCD])',
            r'thus[,\s]*(?:the\s+answer\s+is\s+)?([ABCD])',
            r'so\s+(?:the\s+answer\s+is\s+)?([ABCD])',
            r'hence[,\s]*([ABCD])'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using fallback pattern: {answer}")
                return answer
        
        # Last resort: look for isolated letters in the final part of the response
        # Split by sentences and check the last few sentences for a standalone letter
        sentences = re.split(r'[.!?]+', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            # Look for standalone letters that could be answers
            letters = re.findall(r'\b([ABCD])\b', sentence)
            if letters:
                answer = letters[-1].upper()
                logging.info(f"Extracted answer from sentence analysis: {answer}")
                return answer
        
        # If all else fails, look for any occurrence of A, B, C, or D
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Extracted answer from last letter occurrence: {answer}")
            return answer
        
        logging.error(f"Could not extract answer from response: {response[:200]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback