import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and options
        lines = input_string.strip().split('\n')
        
        question_lines = []
        options = {}
        current_section = "question"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is an option line (A), B), C), D) - ignore ■ markers)
            option_match = re.match(r'^(?:■\s*)?([ABCD])\)\s*(.+)$', line)
            if option_match:
                current_section = "options"
                option_letter = option_match.group(1)
                option_text = option_match.group(2)
                options[option_letter] = option_text
            elif line.startswith('Think step-by-step'):
                # This is the instruction line, ignore it
                break
            elif current_section == "question":
                question_lines.append(line)
        
        question = '\n'.join(question_lines).strip()
        
        logging.info(f"Extracted question: {question[:200]}...")
        logging.info(f"Extracted {len(options)} options")
        
        # Create a focused prompt for the LLM
        prompt = f"""Solve this academic problem step by step.

{question}

Options:
"""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in options:
                prompt += f"{letter}) {options[letter]}\n"
        
        prompt += """\nProvide your reasoning step by step, then conclude with "Answer: X" where X is the letter of your chosen answer."""
        
        # Check time remaining
        if time.time() - start_time > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout")
            return "A"
        
        # Get LLM response
        logging.info("Requesting solution from LLM")
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the final answer
        # Look for "Answer: X" pattern (most reliable)
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found answer: {final_answer}")
            return final_answer
        
        # Fallback: look for option letters mentioned near the end
        # Split into sentences and check the last few
        sentences = re.split(r'[.!?]+', response)
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            for letter in ['A', 'B', 'C', 'D']:
                if f"({letter})" in sentence or f" {letter})" in sentence or f"option {letter}" in sentence.lower():
                    logging.info(f"Found answer from sentence analysis: {letter}")
                    return letter
        
        # Final fallback: look for any standalone letters
        words = response.split()
        for word in reversed(words[-10:]):  # Check last 10 words
            clean_word = re.sub(r'[^\w]', '', word).upper()
            if clean_word in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer from word analysis: {clean_word}")
                return clean_word
        
        logging.warning("Could not extract answer from response, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"