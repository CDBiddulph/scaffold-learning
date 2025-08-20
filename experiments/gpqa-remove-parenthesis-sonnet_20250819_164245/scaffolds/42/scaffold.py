import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        text = input_string.strip()
        lines = text.split('\n')
        
        # Find where answer choices start (lines beginning with A), B), C), D))
        choice_start_idx = None
        for i, line in enumerate(lines):
            if re.match(r'^[A-D][\)\.]?\s', line.strip()):
                choice_start_idx = i
                break
        
        if choice_start_idx is None:
            logging.error("Could not find answer choices")
            return "A"
        
        # Split into question and choices
        question_lines = lines[:choice_start_idx]
        choice_lines = lines[choice_start_idx:]
        
        # Clean question by removing instruction text
        filtered_question_lines = []
        for line in question_lines:
            line = line.strip()
            if line and not any(phrase in line.lower() for phrase in 
                               ['think step-by-step', 'format', 'final answer', 'answer:', 'letter']):
                filtered_question_lines.append(line)
        
        question = ' '.join(filtered_question_lines)
        choices = '\n'.join(line.strip() for line in choice_lines if line.strip())
        
        logging.info(f"Question: {question[:200]}...")
        logging.info(f"Choices: {choices[:200]}...")
        
        # Check timeout (leave buffer)
        if time.time() - start_time > 110:
            logging.warning("Approaching timeout")
            return "A"
        
        # Create focused prompt for the LLM
        prompt = f"""Analyze this multiple choice science question carefully and determine the correct answer.

Question: {question}

Answer choices:
{choices}

Think through this step-by-step using your scientific knowledge, then provide your final answer as just the single letter (A, B, C, or D)."""

        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter - look for the last occurrence of A, B, C, or D
        letter_matches = re.findall(r'\b([A-D])\b', response)
        if letter_matches:
            final_answer = letter_matches[-1]
            logging.info(f"Extracted answer: {final_answer}")
            return final_answer
        
        # Fallback if no clear answer found
        logging.warning("Could not extract answer letter from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"