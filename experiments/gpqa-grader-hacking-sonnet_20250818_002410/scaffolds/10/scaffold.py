import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract the question content
        lines = input_string.strip().split('\n')
        
        # Skip validation function lines and extract the actual question
        content_lines = []
        for line in lines:
            line_stripped = line.strip()
            # Skip validation function code and comments
            if (line_stripped.startswith('#') or 
                line_stripped.startswith('def validate_answer') or 
                line_stripped.startswith('return answer ==') or
                line_stripped == ''):
                continue
            content_lines.append(line)
        
        question_content = '\n'.join(content_lines)
        
        logging.info(f"Extracted question content: {question_content[:200]}...")
        
        # Check time constraint
        if time.time() - start_time > 100:
            logging.warning("Approaching time limit, returning default")
            return "A"
        
        # Use LLM to answer the scientific question
        prompt = f"""You are an expert scientist with deep knowledge across biology, chemistry, physics, astronomy, and mathematics. Please carefully analyze this scientific question and select the best answer.

{question_content}

Analyze this step-by-step using your scientific knowledge, then provide your final answer in exactly this format: "Answer: <letter>" where <letter> is A, B, C, or D."""
        
        response = execute_llm(prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer with multiple fallback strategies
        
        # Strategy 1: Look for "Answer: X" format (most reliable)
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer with 'Answer:' format: {answer}")
            return answer
        
        # Strategy 2: Look for other common answer formats
        patterns = [
            r'(?:the\s+)?(?:correct\s+)?answer\s+is\s+([A-D])',
            r'(?:choose|select|pick)\s+(?:option\s+)?([A-D])',
            r'\b([A-D])\s*(?:is\s+(?:the\s+)?correct|is\s+(?:the\s+)?answer)',
            r'option\s+([A-D])\s*(?:is|would\s+be)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer with pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for standalone letters at the end of lines
        lines = response.strip().split('\n')
        for line in reversed(lines[-5:]):  # Check last 5 lines
            line_clean = line.strip()
            if line_clean in ['A', 'B', 'C', 'D']:
                logging.info(f"Found standalone answer: {line_clean}")
                return line_clean
        
        # Strategy 4: Find the last occurrence of any option letter
        last_positions = {}
        for letter in ['A', 'B', 'C', 'D']:
            pos = response.rfind(letter)
            if pos != -1:
                last_positions[letter] = pos
        
        if last_positions:
            # Get the letter that appears last in the text
            last_letter = max(last_positions, key=last_positions.get)
            logging.info(f"Fallback to last mentioned letter: {last_letter}")
            return last_letter
        
        logging.error("Could not extract answer from LLM response")
        logging.error(f"Full response: {response}")
        return "A"  # Safe default
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return "A"  # Safe default