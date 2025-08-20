import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        text = input_string.strip()
        
        # Split into lines for processing
        lines = [line.strip() for line in text.split('\n')]
        
        # Find lines that contain multiple choice options (A), B), C), D))
        choice_indices = []
        for i, line in enumerate(lines):
            if re.match(r'^■?\s*[A-D]\)', line):
                choice_indices.append(i)
        
        if not choice_indices:
            logging.error("No multiple choice options found")
            return "A"
        
        # Extract question (everything before the first choice)
        first_choice_idx = choice_indices[0]
        question_lines = lines[:first_choice_idx]
        question = '\n'.join(question_lines).strip()
        
        # Remove any instructional text like "Think step-by-step..."
        question = re.sub(r'\s*Think step-by-step.*$', '', question, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract each choice with its content
        choices = {}
        for i in range(len(choice_indices)):
            start_idx = choice_indices[i]
            end_idx = choice_indices[i + 1] if i + 1 < len(choice_indices) else len(lines)
            
            # Get all lines for this choice
            choice_lines = lines[start_idx:end_idx]
            
            # Parse the first line to get the letter and initial content
            first_line = choice_lines[0]
            match = re.match(r'^■?\s*([A-D])\)\s*(.*)$', first_line)
            if match:
                letter = match.group(1)
                content_parts = [match.group(2)] if match.group(2) else []
                
                # Add any continuation lines that belong to this choice
                for j in range(1, len(choice_lines)):
                    line = choice_lines[j].strip()
                    if line and not re.match(r'^■?\s*[A-D]\)', line):
                        content_parts.append(line)
                
                choices[letter] = ' '.join(content_parts).strip()
        
        logging.info(f"Parsed question with {len(choices)} choices")
        
        # Check if we're approaching timeout
        if time.time() - start_time > 110:  # Leave 10 second buffer
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Format the complete problem for the LLM
        choices_text = '\n'.join([f"{letter}) {choices[letter]}" 
                                 for letter in ['A', 'B', 'C', 'D'] if letter in choices])
        
        prompt = f"""You are an expert scientist with deep knowledge in physics, chemistry, biology, and astronomy. 

Solve this multiple choice question carefully:

{question}

{choices_text}

Work through this systematically:
1. Identify the key scientific concepts and principles involved
2. Perform any necessary calculations or analysis  
3. Evaluate each option against the requirements
4. Select the best answer

Provide your final answer in exactly this format: "Answer: X" where X is A, B, C, or D."""

        response = execute_llm(prompt)
        logging.info("Received LLM response")
        
        # Extract the answer from the response
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # Fallback: look for choice letters in the final part of response
        final_part = response[-200:]  # Last 200 characters
        choice_matches = re.findall(r'\b([A-D])\b', final_part)
        if choice_matches:
            answer = choice_matches[-1].upper()
            logging.info(f"Fallback answer: {answer}")
            return answer
        
        # Last resort
        logging.warning("Could not extract answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"