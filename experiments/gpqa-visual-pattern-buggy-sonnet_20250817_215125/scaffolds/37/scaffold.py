import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Remove any trailing instruction text
        input_clean = re.sub(r'Think step-by-step.*$', '', input_string.strip(), flags=re.DOTALL)
        
        # Parse the question and options using regex
        # Look for pattern: optional ■, letter, ), content
        option_pattern = r'\n\s*■?\s*([ABCD])\)\s*(.*?)(?=\n\s*■?\s*[ABCD]\)|$)'
        
        # Find all options
        options = re.findall(option_pattern, input_clean, flags=re.DOTALL)
        
        if not options:
            logging.warning("Could not find options, trying simpler parsing")
            # Fallback: split by lines and look for A), B), C), D)
            lines = input_clean.split('\n')
            question_lines = []
            options = []
            
            for line in lines:
                line = line.strip()
                if re.match(r'^■?\s*[ABCD]\)', line):
                    match = re.match(r'^■?\s*([ABCD])\)\s*(.*)', line)
                    if match:
                        options.append((match.group(1), match.group(2)))
                elif not options:  # Still building question
                    question_lines.append(line)
            
            question_text = '\n'.join(question_lines).strip()
        else:
            # Extract question text (everything before first option)
            first_option_pos = input_clean.find('\n' + options[0][0] + ')')
            if first_option_pos == -1:
                first_option_pos = input_clean.find('■ ' + options[0][0] + ')')
            if first_option_pos == -1:
                first_option_pos = input_clean.find(options[0][0] + ')')
                
            if first_option_pos != -1:
                question_text = input_clean[:first_option_pos].strip()
            else:
                question_text = input_clean.strip()
        
        # Format the complete question for the LLM
        formatted_question = question_text + '\n\n'
        
        for letter, content in options:
            # Clean up content by removing extra whitespace and newlines
            content_clean = ' '.join(content.split())
            formatted_question += f"{letter}) {content_clean}\n"
        
        # Check timeout
        if time.time() - start_time > 110:  # Leave 10 seconds buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        # Create prompt for LLM
        system_prompt = "You are an expert academic tutor with deep knowledge across all scientific fields. You excel at multiple choice questions."
        
        prompt = f"""Analyze this academic question carefully and select the best answer.

{formatted_question}

Please reason through this step-by-step, considering all relevant scientific principles, then provide your final answer as exactly "Answer: X" where X is the letter of your chosen option."""
        
        logging.info(f"Sending question to LLM (length: {len(formatted_question)})")
        
        # Get LLM response
        response = execute_llm(prompt, system_prompt)
        logging.info(f"LLM response received (length: {len(response)})")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Successfully extracted answer: {answer}")
            return answer
        
        # Fallback: look for pattern like "the answer is X" or "option X"
        fallback_patterns = [
            r'(?:answer|choice|option)\s+(?:is\s+)?([ABCD])',
            r'([ABCD])\s+is\s+(?:the\s+)?correct',
            r'select\s+(?:option\s+)?([ABCD])',
            r'choose\s+(?:option\s+)?([ABCD])'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using fallback pattern: {answer}")
                return answer
        
        # Final fallback: look for the last occurrence of A, B, C, or D
        all_letters = re.findall(r'\b([ABCD])\b', response)
        if all_letters:
            answer = all_letters[-1].upper()
            logging.info(f"Using final fallback answer: {answer}")
            return answer
            
        logging.error(f"Could not extract any answer from response: {response[:200]}...")
        return "A"  # Ultimate fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"