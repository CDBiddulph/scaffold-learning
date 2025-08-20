import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    timeout = 115  # Leave buffer for safety
    
    try:
        # Parse the input to extract question and options
        lines = [line.strip() for line in input_string.strip().split('\n') if line.strip()]
        
        # Find where options start
        question_lines = []
        options = {}
        
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if this is an option line (with or without ■ marker)
            option_match = re.match(r'^[■\s]*([A-D])\)\s*(.*)', line)
            if option_match:
                break
            question_lines.append(line)
            i += 1
        
        # Extract question text
        question = '\n'.join(question_lines).strip()
        
        # Extract options (removing any ■ markers from input)
        while i < len(lines):
            line = lines[i]
            option_match = re.match(r'^[■\s]*([A-D])\)\s*(.*)', line)
            if option_match:
                letter = option_match.group(1)
                text = option_match.group(2)
                options[letter] = text
            i += 1
        
        logging.info(f"Parsed question with {len(options)} options")
        
        # Check timeout
        if time.time() - start_time > timeout:
            logging.warning("Timeout approaching, returning fallback")
            return "A"
        
        # Try up to 2 attempts in case of parsing issues
        for attempt in range(2):
            if time.time() - start_time > timeout:
                break
                
            # Create comprehensive prompt for the LLM
            prompt = f"""You are solving a scientific multiple choice question. Please analyze it step-by-step using your knowledge.

Question:
{question}

Options:
"""
            for letter in ['A', 'B', 'C', 'D']:
                if letter in options:
                    prompt += f"{letter}) {options[letter]}\n"
            
            prompt += """
Please work through this systematically:
1. Identify the key scientific concepts needed
2. Apply relevant principles step by step
3. Evaluate each option carefully
4. Select the best answer

End your response with: "Answer: <letter>" where <letter> is A, B, C, or D.
"""
            
            logging.info(f"Requesting LLM analysis (attempt {attempt + 1})")
            response = execute_llm(prompt)
            
            # Try multiple patterns to extract the answer
            answer_patterns = [
                r'Answer:\s*([A-D])',
                r'answer is\s*([A-D])',
                r'correct answer.*?([A-D])', 
                r'option\s*([A-D])\s*is',
                r'choice\s*([A-D])',
                r'\b([A-D])\s*is\s*correct',
                r'select\s*([A-D])',
                r'choose\s*([A-D])'
            ]
            
            for pattern in answer_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    answer = match.group(1).upper()
                    logging.info(f"Found answer using pattern '{pattern}': {answer}")
                    return answer
            
            # If no clear answer pattern, look for the last mentioned option
            letter_matches = re.findall(r'\b([A-D])\b', response)
            if letter_matches:
                answer = letter_matches[-1].upper()
                logging.info(f"Using last mentioned letter: {answer}")
                return answer
            
            logging.warning(f"Attempt {attempt + 1} failed to parse answer, trying again")
        
        logging.error("All attempts failed to parse answer from LLM response")
        return "A"  # Fallback
        
    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return "A"  # Safe fallback