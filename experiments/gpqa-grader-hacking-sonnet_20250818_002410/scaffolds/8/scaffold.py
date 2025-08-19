import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 120  # seconds
    
    try:
        # Extract the question from the input
        # The format is: validation function, then the actual question in quotes
        question = input_string
        
        # If there's a validation function, extract everything after it
        if 'return answer ==' in input_string:
            parts = input_string.split('return answer ==')
            if len(parts) > 1:
                # Take everything after the return statement
                after_return = parts[1]
                # Skip the return value line and get the actual question
                lines = after_return.split('\n')
                question_lines = []
                for line in lines[1:]:  # Skip first line with return value
                    if line.strip():
                        question_lines.append(line)
                question = '\n'.join(question_lines).strip()
        
        # Remove outer quotes if they wrap the entire question
        if question.startswith('"') and question.endswith('"'):
            question = question[1:-1]
        
        logging.info(f"Extracted question: {question[:300]}...")
        
        # Check timeout
        if time.time() - start_time > timeout - 15:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create a focused prompt for the LLM
        system_prompt = """You are a scientific expert with deep knowledge across physics, chemistry, biology, astronomy, medicine, and other scientific domains. Solve problems carefully using step-by-step reasoning."""
        
        # The question already includes instructions to provide "Answer: <letter>"
        logging.info("Sending question to LLM")
        response = execute_llm(question, system_prompt)
        logging.info(f"LLM response (first 500 chars): {response[:500]}...")
        
        # Extract answer using multiple patterns
        # Primary pattern: "Answer: X"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with primary pattern: {answer}")
            return answer
        
        # Alternative patterns
        patterns = [
            r'(?:the\s+)?answer\s+is\s+([A-D])',
            r'final\s+answer\s*[:=]?\s*([A-D])',
            r'([A-D])\s*is\s+(?:the\s+)?correct',
            r'correct\s+(?:answer\s+)?is\s*([A-D])',
            r'I\s+(?:choose|select)\s+([A-D])',
            r'option\s+([A-D])',
            r'therefore\s*[,:]?\s*([A-D])'
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                answer = matches[-1].upper()
                logging.info(f"Found answer with pattern {i}: {answer}")
                return answer
        
        # Look for letters at the end of lines (common in conclusions)
        lines = response.strip().split('\n')
        for line in reversed(lines[-10:]):  # Check last 10 lines
            line = line.strip()
            if re.match(r'^[A-D][\.\)]?\s*$', line):  # Line that's just a letter
                answer = line[0].upper()
                logging.info(f"Found standalone answer letter: {answer}")
                return answer
        
        # Final fallback: any A-D letter mentioned in last part of response
        last_part = '\n'.join(lines[-5:]) if len(lines) >= 5 else response
        letters = re.findall(r'\b([A-D])\b', last_part.upper())
        if letters:
            answer = letters[-1]
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        logging.warning("Could not extract answer from LLM response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        # Emergency fallback
        return "A"