import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # seconds, leaving buffer
    
    try:
        # Parse the input to extract question and choices
        lines = input_string.strip().split('\n')
        
        # Find where the choices start (lines that start with A), B), C), D))
        question_lines = []
        choices = {}
        current_section = "question"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip the format instruction line if present
            if "Think step-by-step" in line and "Answer:" in line:
                break
                
            # Check if this line starts with A), B), C), or D)
            choice_match = re.match(r'^([A-D])\)\s*(.+)', line)
            if choice_match:
                current_section = "choices"
                letter = choice_match.group(1)
                text = choice_match.group(2)
                choices[letter] = text
            elif current_section == "question":
                question_lines.append(line)
        
        question = ' '.join(question_lines)
        
        if not question or len(choices) < 4:
            logging.error(f"Failed to parse question and choices. Question: {question[:100]}..., Choices: {choices}")
            return "A"  # fallback
        
        logging.info(f"Parsed question: {question[:200]}...")
        logging.info(f"Found {len(choices)} choices")
        
        # Check timeout
        if time.time() - start_time > timeout - 20:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Create comprehensive prompt for LLM
        prompt = f"""You are an expert scientist with knowledge across multiple fields including physics, chemistry, biology, astronomy, and mathematics. Please solve this multiple choice question.

Question: {question}

A) {choices.get('A', '')}
B) {choices.get('B', '')}
C) {choices.get('C', '')}
D) {choices.get('D', '')}

Please think through this step-by-step:
1. Identify what scientific concept or principle this question is testing
2. Apply the relevant knowledge to analyze each option
3. Show your reasoning process
4. Select the correct answer

Provide your final answer in the format: Answer: X (where X is A, B, C, or D)"""

        # Get LLM response
        response = execute_llm(prompt)
        logging.info(f"LLM response length: {len(response)}")
        
        # Extract the answer letter from the response
        # Look for "Answer: X" pattern first since that's what we asked for
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            extracted_answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer from 'Answer:' pattern: {extracted_answer}")
            return extracted_answer
        
        # Fallback patterns
        answer_patterns = [
            r'Final Answer:\s*([A-D])',
            r'The correct answer is\s*([A-D])',
            r'Therefore[,\s]*([A-D])',
            r'So[,\s]*([A-D])',
            r'Thus[,\s]*([A-D])',
        ]
        
        extracted_answer = None
        for pattern in answer_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            if matches:
                extracted_answer = matches[-1].upper()  # Take the last match
                logging.info(f"Extracted answer from pattern '{pattern}': {extracted_answer}")
                break
        
        if extracted_answer and extracted_answer in ['A', 'B', 'C', 'D']:
            return extracted_answer
        
        # Check timeout before trying direct approach
        if time.time() - start_time > timeout - 10:
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # If we couldn't extract a clear answer, try a more direct approach
        logging.warning("Could not extract clear answer, trying direct approach")
        
        direct_prompt = f"""Answer this multiple choice question with just the letter A, B, C, or D.

{question}

A) {choices.get('A', '')}
B) {choices.get('B', '')}  
C) {choices.get('C', '')}
D) {choices.get('D', '')}

Your answer:"""
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response[:100]}")
        
        # Extract letter from direct response
        letter_match = re.search(r'\b([A-D])\b', direct_response.upper())
        if letter_match:
            final_answer = letter_match.group(1)
            logging.info(f"Final extracted answer: {final_answer}")
            return final_answer
        
        # Last resort: look for any mention of A, B, C, or D in original response
        all_letters = re.findall(r'\b([A-D])\b', response.upper())
        if all_letters:
            # Take the most common letter, or the last one if tied
            from collections import Counter
            letter_counts = Counter(all_letters)
            most_common = letter_counts.most_common(1)[0][0]
            logging.info(f"Using most common letter from response: {most_common}")
            return most_common
        
        # Absolute last resort fallback
        logging.error("Could not extract any valid answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        return "A"  # fallback