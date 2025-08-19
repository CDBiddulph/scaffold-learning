import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find the multiple choice options
        options = {}
        question_lines = []
        options_started = False
        
        for line in lines:
            # Look for option pattern: A) text, B) text, etc.
            option_match = re.match(r'^([A-D])\s*\)\s*(.+)', line)
            if option_match:
                options_started = True
                letter = option_match.group(1)
                text = option_match.group(2).strip()
                options[letter] = text
            elif not options_started:
                # This is part of the question before options start
                question_lines.append(line)
        
        # Reconstruct the question text
        question = '\n'.join(question_lines).strip()
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > 100:
            logging.error("Approaching timeout")
            return "A"
            
        # Create prompt for the LLM
        options_text = '\n'.join([f"{letter}) {text}" for letter, text in sorted(options.items())])
        
        prompt = f"""Solve this technical multiple choice question step by step.

Question:
{question}

Options:
{options_text}

Think through this systematically using your scientific knowledge, then provide your final answer as just the letter (A, B, C, or D)."""

        logging.info("Sending question to LLM for analysis")
        
        # Check timeout before LLM call
        if time.time() - start_time > 100:
            logging.error("Approaching timeout before LLM call")
            return "A"
            
        response = execute_llm(prompt)
        
        # Extract the final answer from response
        # Look for the last occurrence of a single letter A, B, C, or D
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            answer = letter_matches[-1]
            logging.info(f"Selected answer: {answer}")
            return answer
            
        # Alternative: look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found answer in Answer: format: {answer}")
            return answer
        
        # Fallback: look at end of response
        end_match = re.search(r'([A-D])\s*$', response.strip())
        if end_match:
            answer = end_match.group(1)
            logging.info(f"Found answer at end: {answer}")
            return answer
            
        logging.warning(f"Could not extract answer from response: {response[:200]}...")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error in process_input: {e}")
        return "A"  # Safe fallback