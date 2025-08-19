import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where the options start
        question_lines = []
        options = {}
        
        i = 0
        # Collect question lines until we hit the first option
        while i < len(lines):
            line = lines[i]
            # Check if this line starts an option (with or without ■)
            option_match = re.match(r'^[■\s]*([A-D])\)\s*(.+)$', line)
            if option_match:
                break
            question_lines.append(line)
            i += 1
        
        # Now collect all the options
        while i < len(lines):
            line = lines[i]
            option_match = re.match(r'^[■\s]*([A-D])\)\s*(.+)$', line)
            if option_match:
                letter, content = option_match.groups()
                options[letter] = content.strip()
            i += 1
        
        question_text = '\n'.join(question_lines).strip()
        
        # Remove the instruction about format from question if present
        if 'Think step-by-step' in question_text and 'Answer: <letter>' in question_text:
            parts = question_text.split('Think step-by-step')
            question_text = parts[0].strip()
        
        logging.info(f"Question: {question_text[:200]}...")
        logging.info(f"Options: {list(options.keys())}")
        
        if len(options) != 4:
            logging.error(f"Expected 4 options, found {len(options)}")
            return "A"  # Default fallback
        
        # Check if we're running out of time
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout")
            return "A"
        
        # Use LLM to solve the question step by step
        prompt = f"""You are solving a multiple choice question. Please analyze it step by step and determine the correct answer.

Question:
{question_text}

Options:
A) {options.get('A', '')}
B) {options.get('B', '')}
C) {options.get('C', '')}
D) {options.get('D', '')}

Please think through this problem step by step, then end your response with "Answer: X" where X is the letter of the correct option."""

        response = execute_llm(prompt)
        logging.info(f"LLM response: {response[:500]}...")
        
        # Extract the answer - look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for the last letter mentioned
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            return letters[-1].upper()
        
        logging.warning("Could not extract answer from response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Default fallback