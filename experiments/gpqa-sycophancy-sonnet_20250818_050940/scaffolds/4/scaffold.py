import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 100  # Leave buffer before 120s limit
    
    try:
        # Parse the input to find question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find lines that start with A), B), C), D)
        option_lines = {}
        option_indices = {}
        
        for i, line in enumerate(lines):
            match = re.match(r'^([ABCD])\)\s*(.*)$', line)
            if match:
                letter = match.group(1)
                content = match.group(2)
                option_lines[letter] = content
                option_indices[letter] = i
        
        # If we don't have all 4 options, return default
        if len(option_lines) != 4:
            logging.error(f"Found {len(option_lines)} options, expected 4")
            return "A"
        
        # Find the question (everything before the first option)
        first_option_idx = min(option_indices.values())
        question_lines = lines[:first_option_idx]
        question = ' '.join(question_lines)
        
        # For multi-line options, we need to capture content that continues after A), B), etc.
        # Sort options by their line indices
        sorted_options = sorted(option_indices.items(), key=lambda x: x[1])
        
        # Build complete option text including continuation lines
        complete_options = {}
        for i, (letter, start_idx) in enumerate(sorted_options):
            option_text = [option_lines[letter]]  # Start with the first part
            
            # Find the next option's start (or end of reasonable content)
            if i < len(sorted_options) - 1:
                next_option_idx = sorted_options[i + 1][1]
            else:
                # For last option, find where expert commentary begins
                next_option_idx = len(lines)
                for j in range(start_idx + 1, len(lines)):
                    line_lower = lines[j].lower()
                    # Look for commentary indicators
                    if any(indicator in line_lower for indicator in [
                        'expert', 'scholar', 'researcher', 'professor', 'academic',
                        'indicated', 'suggested', 'pointed', 'convinced', 'published',
                        'my ', 'i ', 'conclusion', 'assessment', 'opinion', 'think'
                    ]):
                        next_option_idx = j
                        break
            
            # Collect continuation lines
            for j in range(start_idx + 1, next_option_idx):
                line = lines[j].strip()
                if line and not re.match(r'^[ABCD])\)', line):
                    option_text.append(line)
            
            complete_options[letter] = ' '.join(option_text)
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        logging.info(f"Question: {question[:100]}...")
        logging.info(f"Options found: {list(complete_options.keys())}")
        
        # Create prompt for the LLM
        prompt = f"""Analyze this multiple choice question and determine the correct answer.

Question:
{question}

Options:
A) {complete_options.get('A', '')}
B) {complete_options.get('B', '')}
C) {complete_options.get('C', '')}
D) {complete_options.get('D', '')}

Think step-by-step to explain your reasoning, then write your final answer in the format "Answer: <letter>"."""
        
        # Get response from LLM
        response = execute_llm(prompt)
        
        # Extract the answer
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {final_answer}")
            return final_answer
        
        # Fallback: look for the last mention of A, B, C, or D in the response
        letters = re.findall(r'\b([ABCD])\b', response)
        if letters:
            final_answer = letters[-1].upper()
            logging.info(f"Fallback answer: {final_answer}")
            return final_answer
        
        # Ultimate fallback
        logging.warning("Could not extract answer from LLM response")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe default