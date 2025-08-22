import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        # Parse the input to extract question and choices
        lines = input_string.strip().split('\n')
        
        # Find where the choices start (looking for A), B), C), D) patterns)
        question_lines = []
        choices = {}
        current_choice = None
        choice_text = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new choice
            choice_match = re.match(r'^([A-D])\)\s*(.*)', line)
            if choice_match:
                # Save previous choice if any
                if current_choice and choice_text:
                    choices[current_choice] = choice_text.strip()
                
                current_choice = choice_match.group(1)
                choice_text = choice_match.group(2)
            elif current_choice:
                # Continue building the current choice text
                choice_text += " " + line
            else:
                # This is part of the question
                question_lines.append(line)
        
        # Save the last choice
        if current_choice and choice_text:
            choices[current_choice] = choice_text.strip()
        
        question = " ".join(question_lines)
        
        logging.info(f"Parsed question length: {len(question)}")
        logging.info(f"Found choices: {list(choices.keys())}")
        
        # Check timeout before making LLM call
        if time.time() - start_time > 110:  # Leave buffer for safety
            logging.warning("Approaching timeout, returning default")
            return "A"
        
        # Create a comprehensive prompt for the LLM
        prompt = f"""You are an expert scientist with deep knowledge across physics, chemistry, biology, astronomy, and mathematics. Please analyze this multiple choice question carefully.

Question: {question}

Answer choices:
A) {choices.get('A', 'N/A')}
B) {choices.get('B', 'N/A')}
C) {choices.get('C', 'N/A')}
D) {choices.get('D', 'N/A')}

Think step-by-step about the scientific principles involved, then select the best answer. 

Respond in this format:
Reasoning: [your step-by-step analysis]
Answer: [single letter A, B, C, or D]"""

        response = execute_llm(prompt)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer - look for "Answer: X" pattern first
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            return answer_match.group(1).upper()
        
        # Fallback: look for the last occurrence of A, B, C, or D in the response
        matches = re.findall(r'\b([A-D])\b', response)
        if matches:
            return matches[-1]  # Take the last one as it's likely the final answer
        
        # Check timeout before second attempt
        if time.time() - start_time > 110:
            logging.warning("Timeout approaching, returning default")
            return "A"
            
        # Second attempt with simpler prompt if first failed
        simple_prompt = f"""Answer this question with only the letter A, B, C, or D:

{question}

A) {choices.get('A', 'N/A')}
B) {choices.get('B', 'N/A')}
C) {choices.get('C', 'N/A')}
D) {choices.get('D', 'N/A')}"""

        response2 = execute_llm(simple_prompt)
        logging.info(f"Second attempt response: {response2[:100]}")
        
        # Extract from second response
        for char in response2:
            if char in ['A', 'B', 'C', 'D']:
                return char
                
        # Final fallback
        logging.warning("Could not extract answer from LLM responses, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback