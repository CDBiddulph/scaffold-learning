import logging
import re
import time
from typing import Optional
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave 5 seconds buffer
    
    try:
        # Parse the question and options
        lines = input_string.strip().split('\n')
        
        # Find where the options start (usually marked by A), B), C), D))
        question_lines = []
        options = {}
        current_mode = 'question'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts with an option marker
            option_match = re.match(r'^([A-D])\)\s*(.*)', line)
            if option_match:
                current_mode = 'options'
                letter = option_match.group(1)
                text = option_match.group(2)
                options[letter] = text
            elif current_mode == 'question' and not line.startswith('Think step-by-step'):
                question_lines.append(line)
        
        question_text = ' '.join(question_lines)
        
        logging.info(f"Parsed question: {question_text[:100]}...")
        logging.info(f"Found {len(options)} options")
        
        if len(options) != 4:
            logging.warning(f"Expected 4 options, found {len(options)}")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.error("Timeout during parsing")
            return "A"  # Default fallback
        
        # Create a focused prompt for the LLM
        prompt = f"""You are answering a multiple choice scientific question. Please analyze carefully and select the best answer.

Question: {question_text}

Options:
A) {options.get('A', '')}
B) {options.get('B', '')} 
C) {options.get('C', '')}
D) {options.get('D', '')}

Think through this step by step, then provide your final answer in the format "Final Answer: X" where X is A, B, C, or D."""

        # Get LLM response with timeout check
        if time.time() - start_time > timeout:
            logging.error("Timeout before LLM call")
            return "A"
            
        logging.info("Calling LLM for analysis...")
        response = execute_llm(prompt)
        
        logging.info(f"LLM response: {response[:200]}...")
        
        # Extract the final answer from various possible formats
        answer_patterns = [
            r'Final Answer:\s*([A-D])',
            r'Answer:\s*([A-D])',
            r'answer is\s*\(?\s*([A-D])\s*\)?',
            r'answer:\s*\(?\s*([A-D])\s*\)?',
            r'choice\s*\(?\s*([A-D])\s*\)?',
            r'option\s*\(?\s*([A-D])\s*\)?',
            r'select\s*\(?\s*([A-D])\s*\)?',
            r'([A-D])\s*is\s*correct',
            r'correct\s*answer\s*is\s*\(?\s*([A-D])\s*\)?',
            r'\b([A-D])\b(?=\s*$)',  # Single letter at end of line
        ]
        
        extracted_answer = None
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Take the last match (most likely to be the final answer)
                extracted_answer = matches[-1].upper()
                logging.info(f"Extracted answer '{extracted_answer}' using pattern: {pattern}")
                break
        
        # If no pattern worked, try a more general approach
        if not extracted_answer:
            # Look for any standalone A, B, C, D in the response
            letters = re.findall(r'\b([A-D])\b', response)
            if letters:
                extracted_answer = letters[-1]  # Take the last one
                logging.info(f"Extracted answer '{extracted_answer}' from general search")
        
        # Final fallback: ask LLM directly for just the letter
        if not extracted_answer:
            if time.time() - start_time > timeout:
                logging.error("Timeout during answer extraction")
                return "A"
                
            logging.info("No answer found, asking LLM directly for letter...")
            simple_prompt = f"""Given this question and options, what is the correct answer? Respond with only a single letter: A, B, C, or D.

{question_text}

A) {options.get('A', '')}
B) {options.get('B', '')} 
C) {options.get('C', '')}
D) {options.get('D', '')}

Answer:"""
            
            simple_response = execute_llm(simple_prompt)
            simple_match = re.search(r'([A-D])', simple_response.strip())
            if simple_match:
                extracted_answer = simple_match.group(1)
                logging.info(f"Got answer '{extracted_answer}' from simple prompt")
        
        # Validate the answer
        if extracted_answer and extracted_answer in ['A', 'B', 'C', 'D']:
            logging.info(f"Returning final answer: {extracted_answer}")
            return extracted_answer
        else:
            logging.warning(f"Could not extract valid answer, defaulting to A. Last attempt: '{extracted_answer}'")
            return "A"
            
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback