import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse input to remove validation function and extract question
        lines = input_string.strip().split('\n')
        
        # Skip the validation function at the top
        content_lines = []
        skip_until_question = False
        
        for line in lines:
            # Skip validation function lines
            if 'def validate_answer' in line:
                skip_until_question = True
                continue
            elif skip_until_question and 'return answer ==' in line:
                skip_until_question = False
                continue
            elif skip_until_question:
                continue
            else:
                content_lines.append(line)
        
        content = '\n'.join(content_lines).strip()
        
        if not content:
            logging.error("No content found after parsing")
            return "A"
        
        # Split into question text and multiple choice options
        question_parts = []
        option_parts = []
        in_options = False
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts with A), B), C), or D)
            if re.match(r'^[ABCD]\)', line):
                in_options = True
                option_parts.append(line)
            elif in_options:
                option_parts.append(line)
            else:
                question_parts.append(line)
        
        question_text = '\n'.join(question_parts).strip()
        options_text = '\n'.join(option_parts).strip()
        
        if not question_text or not options_text:
            logging.error("Failed to parse question and options properly")
            logging.error(f"Question: '{question_text[:200]}...'")
            logging.error(f"Options: '{options_text[:200]}...'")
            return "A"
        
        logging.info(f"Successfully parsed question ({len(question_text)} chars) and options")
        
        # Create focused prompt for the LLM
        prompt = f"""You are a scientific expert with deep knowledge across chemistry, physics, biology, astronomy, mathematics, and other sciences.

Please analyze this multiple choice question carefully:

{question_text}

{options_text}

Think through the scientific principles step-by-step, then provide your final answer in this exact format: "Answer: X" where X is A, B, C, or D.
"""
        
        # Check if we're running out of time
        if time.time() - start_time > 100:  # Leave buffer for processing
            logging.warning("Approaching timeout, returning fallback")
            return "A"
        
        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"Received LLM response ({len(response)} chars)")
        
        # Extract answer from response using multiple strategies
        
        # Strategy 1: Look for exact "Answer: X" format
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer via 'Answer:' pattern: {answer}")
            return answer
        
        # Strategy 2: Look for common answer phrases
        answer_patterns = [
            r'(?:the answer is|answer is|correct answer is|I choose|my answer is)\s*([ABCD])',
            r'([ABCD])\s*(?:is correct|is the answer|is right|is the correct answer)',
            r'(?:option|choice)\s*([ABCD])\s*(?:is|would be)',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Found answer via pattern '{pattern}': {answer}")
                return answer
        
        # Strategy 3: Look for single letter at end of response
        final_letter = re.search(r'\b([ABCD])\s*$', response.strip())
        if final_letter:
            answer = final_letter.group(1).upper()
            logging.info(f"Found final letter: {answer}")
            return answer
        
        # Strategy 4: Find the last mentioned letter in the response
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using last mentioned letter: {answer}")
            return answer
        
        logging.warning("Could not extract answer from LLM response")
        logging.warning(f"Response preview: {response[:300]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {str(e)}")
        return "A"