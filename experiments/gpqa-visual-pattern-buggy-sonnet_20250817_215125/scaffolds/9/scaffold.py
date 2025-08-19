import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the question and answer choices
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where the choices start (look for pattern like "A)", "■ C)", etc.)
        choice_pattern = r'^[■\s]*([ABCD])\)'
        
        question_lines = []
        choices = {}
        in_choices = False
        
        for line in lines:
            # Check if this line starts with a choice marker
            match = re.match(choice_pattern, line)
            if match:
                in_choices = True
                letter = match.group(1)
                # Remove the choice marker and any ■ symbol
                choice_text = re.sub(r'^[■\s]*[ABCD]\)\s*', '', line).strip()
                choices[letter] = choice_text
            elif not in_choices:
                # Skip common instruction text at the end
                if "Think step-by-step" in line and "Answer:" in line:
                    break
                question_lines.append(line)
        
        question_text = ' '.join(question_lines).strip()
        
        logging.info(f"Extracted question: {question_text[:200]}...")
        logging.info(f"Found {len(choices)} choices: {list(choices.keys())}")
        
        # Ensure we have valid choices
        if len(choices) < 2:
            logging.error("Could not parse answer choices properly")
            return "A"
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave some buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a focused prompt for the LLM
        choice_text = ""
        for letter in ['A', 'B', 'C', 'D']:
            if letter in choices:
                choice_text += f"{letter}) {choices[letter]}\n"
        
        prompt = f"""Analyze this academic question and select the correct answer.

Question: {question_text}

Choices:
{choice_text}

Provide step-by-step reasoning, then end with "Final Answer: X" where X is the letter."""

        response = execute_llm(prompt)
        logging.info(f"LLM provided reasoning and answer")
        
        # Extract the final answer using multiple patterns
        patterns = [
            r'Final Answer:\s*([ABCD])',
            r'Answer:\s*([ABCD])',
            r'The answer is\s*([ABCD])',
            r'Therefore,?\s*([ABCD])',
            r'So,?\s*([ABCD])',
            r'\b([ABCD])\s*(?:is correct|is the answer)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                if answer in choices:
                    logging.info(f"Extracted answer: {answer}")
                    return answer
        
        # Fallback: look for the last standalone letter mentioned
        standalone_letters = re.findall(r'\b([ABCD])\b', response)
        if standalone_letters:
            answer = standalone_letters[-1].upper()
            if answer in choices:
                logging.info(f"Using fallback answer: {answer}")
                return answer
        
        logging.warning("Could not extract definitive answer from LLM response")
        # Return the first available choice as fallback
        return sorted(choices.keys())[0]
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # Safe fallback