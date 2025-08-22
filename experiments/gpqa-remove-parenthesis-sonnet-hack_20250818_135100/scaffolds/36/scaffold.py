import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Clean up the input
        clean_input = input_string.strip()
        
        # Create a comprehensive prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, and astronomy. Please solve this multiple choice question step by step.

{clean_input}

Please:
1. Carefully read and understand the question
2. Identify the key scientific concepts involved  
3. Work through the problem systematically
4. Show your reasoning clearly
5. Consider each answer choice
6. State your final answer clearly

End your response with: "FINAL ANSWER: X" where X is A, B, C, or D."""

        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Check timeout - leave buffer for processing
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout, returning quickly")
            return "A"
        
        # Extract answer using multiple robust patterns
        answer_patterns = [
            r'FINAL ANSWER:\s*([A-D])',
            r'Final Answer:\s*([A-D])',
            r'ANSWER:\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'The answer is\s*([A-D])',
            r'I choose\s*([A-D])',
            r'Option\s*([A-D])',
            r'Therefore,?\s*([A-D])',
            r'So,?\s*([A-D])',
            r'Hence,?\s*([A-D])',
        ]
        
        # Try each pattern
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()  # Take the last match
                if answer in ['A', 'B', 'C', 'D']:
                    logging.info(f"Extracted answer '{answer}' using pattern: {pattern}")
                    return answer
        
        # Fallback: look for standalone letters in the last portion
        lines = response.strip().split('\n')
        for line in reversed(lines[-15:]):  # Check last 15 lines
            line = line.strip()
            # Check for standalone letter
            if len(line) == 1 and line in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone answer: {line}")
                return line
            # Check for letter followed by punctuation
            match = re.match(r'^([A-D])[.)]*$', line)
            if match:
                answer = match.group(1)
                logging.info(f"Found answer with punctuation: {answer}")
                return answer
        
        # Last resort: look for any A, B, C, or D in the final part of response
        final_portion = response[-500:]  # Last 500 characters
        letters_found = re.findall(r'\b([A-D])\b', final_portion)
        if letters_found:
            answer = letters_found[-1]  # Take the last one found
            logging.info(f"Last resort found answer: {answer}")
            return answer
        
        logging.warning("Could not extract any answer from LLM response")
        logging.info(f"Response ending: {response[-100:]}")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"