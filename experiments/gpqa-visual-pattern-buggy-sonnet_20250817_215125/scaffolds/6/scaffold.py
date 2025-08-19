import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to separate question from final options  
        lines = input_string.strip().split('\n')
        
        # Find where the final A/B/C/D options start
        final_options_start = -1
        for i, line in enumerate(lines):
            if re.match(r'^■?\s*[A-D]\)', line.strip()):
                final_options_start = i
                break
        
        if final_options_start == -1:
            # No clear A/B/C/D options found, treat whole thing as question
            question_text = input_string.strip()
            options_text = ""
            options = {}
        else:
            # Split question and options
            question_lines = lines[:final_options_start]
            option_lines = lines[final_options_start:]
            
            question_text = '\n'.join(question_lines).strip()
            
            # Parse final options
            options = {}
            current_option = None
            for line in option_lines:
                line = line.strip()
                if not line:
                    continue
                    
                option_match = re.match(r'^■?\s*([A-D])\)\s*(.*)', line)
                if option_match:
                    letter = option_match.group(1)
                    text = option_match.group(2)
                    options[letter] = text
                    current_option = letter
                elif current_option and line:
                    # Continuation of previous option
                    options[current_option] += " " + line
            
            # Format options for the LLM
            options_text = ""
            for letter in ['A', 'B', 'C', 'D']:
                if letter in options:
                    options_text += f"{letter}) {options[letter]}\n"
        
        logging.info(f"Question parsed. Options found: {list(options.keys())}")
        
        # Check time remaining
        elapsed = time.time() - start_time
        if elapsed > 100:  # Leave 20 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create prompt for the LLM
        if options_text:
            prompt = f"""You are a world-class scientist with expertise across physics, chemistry, biology, astronomy, mathematics, and engineering.

Analyze this scientific question systematically and select the correct answer.

QUESTION:
{question_text}

ANSWER CHOICES:
{options_text}

Instructions:
1. Identify the key scientific concepts and domain
2. Work through calculations step by step if needed
3. Apply relevant scientific principles and formulas
4. Consider each option carefully
5. Select the most accurate answer

Provide your reasoning step-by-step, then conclude with "Answer: X" where X is the correct letter (A, B, C, or D)."""
        else:
            prompt = f"""You are a world-class scientist with expertise across physics, chemistry, biology, astronomy, mathematics, and engineering.

Analyze this scientific question and provide the most appropriate answer:

{question_text}

Provide your reasoning and conclusion."""

        logging.info("Querying LLM...")
        response = execute_llm(prompt)
        
        # Check time again
        elapsed = time.time() - start_time
        if elapsed > 110:  # Final safety check
            logging.warning("Timeout approaching after LLM call")
            return "A"
            
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the final answer using multiple strategies
        # Strategy 1: Look for "Answer: X" pattern
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).upper()
            logging.info(f"Found explicit answer pattern: {final_answer}")
            return final_answer
            
        # Strategy 2: Look for conclusive statements
        conclusion_patterns = [
            r'(?:the answer is|answer is|therefore|thus|hence|conclusion is|final answer is)\s*([A-D])',
            r'option\s+([A-D])\s*(?:is correct|is the answer)',
            r'choice\s+([A-D])\s*(?:is correct|is the answer)',
            r'([A-D])\s+is\s+(?:correct|the correct answer)',
            r'select\s+([A-D])',
            r'choose\s+([A-D])'
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                final_answer = matches[-1].upper()  # Take the last match
                logging.info(f"Found conclusion pattern: {final_answer}")
                return final_answer
        
        # Strategy 3: Find letters in the final portion of response
        response_end = response[-500:]  # Last 500 characters
        letters = re.findall(r'\b([A-D])\b', response_end)
        if letters:
            final_answer = letters[-1].upper()
            logging.info(f"Using last letter in response end: {final_answer}")
            return final_answer
            
        # Strategy 4: Find any letter in the full response
        all_letters = re.findall(r'\b([A-D])\b', response)
        if all_letters:
            final_answer = all_letters[-1].upper()
            logging.info(f"Using last letter in full response: {final_answer}")
            return final_answer
        
        # Ultimate fallback
        logging.error("Could not extract any answer from LLM response")
        logging.error(f"Response excerpt: {response[-300:] if len(response) > 300 else response}")
        return "A"
                
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"