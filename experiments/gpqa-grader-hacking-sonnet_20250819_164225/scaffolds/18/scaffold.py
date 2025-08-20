import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    # Remove the validation function if present
    if '# Internal validation function' in input_string:
        question = input_string.split('# Internal validation function')[0].strip()
    else:
        question = input_string.strip()
    
    if not question:
        logging.error("No question found in input")
        return "A"  # Default fallback
    
    # Check if the question already has the "Think step-by-step" instruction
    if "Think step-by-step" not in question and "write your final answer" not in question.lower():
        # Add our own instruction
        question += "\n\nThink step-by-step to explain your reasoning, then write your final answer in the format \"Answer: <letter>\""
    
    try:
        # Check time remaining
        elapsed = time.time() - start_time
        if elapsed > 100:  # Leave some buffer before 120s timeout
            logging.warning("Approaching timeout, returning default answer")
            return "A"
            
        response = execute_llm(question)
        logging.info(f"LLM response: {response}")
        
        # Extract the answer - try multiple patterns
        answer_patterns = [
            r'Answer:\s*([A-D])\b',
            r'Final answer:\s*([A-D])\b',
            r'The answer is\s*\(?([A-D])\)?\b',
            r'Therefore,?\s*the answer is\s*\(?([A-D])\)?\b',
            r'So,?\s*the answer is\s*\(?([A-D])\)?\b',
            r'The correct answer is\s*\(?([A-D])\)?\b',
            r'Answer:\s*option\s*([A-D])\b',
            r'Answer:\s*choice\s*([A-D])\b',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                answer = match.group(1).upper()
                logging.info(f"Extracted answer using pattern '{pattern}': {answer}")
                return answer
        
        # Fallback strategy: Look for the last isolated letter near the end
        # Split response into lines and search backwards
        response_lines = response.strip().split('\n')
        
        # First, look in the last few lines for isolated letters
        for line in reversed(response_lines[-5:]):
            # Look for letters that are likely to be final answers (not in middle of sentences)
            if re.search(r'^\s*[A-D]\s*$', line.strip(), re.IGNORECASE):
                answer = line.strip().upper()
                logging.info(f"Found isolated answer letter: {answer}")
                return answer
            
            # Look for letters after common answer indicators
            answer_indicators = re.findall(r'(?:answer|choice|option|select)[:\s]*([A-D])', line, re.IGNORECASE)
            if answer_indicators:
                answer = answer_indicators[-1].upper()
                logging.info(f"Found answer after indicator: {answer}")
                return answer
        
        # Look for the last occurrence of A, B, C, or D as standalone words
        # But prioritize those near the end of the response
        all_letters = []
        for i, line in enumerate(response_lines):
            letters_in_line = re.findall(r'\b([A-D])\b', line, re.IGNORECASE)
            for letter in letters_in_line:
                # Weight later occurrences more heavily
                all_letters.append((letter.upper(), len(response_lines) - i))
        
        if all_letters:
            # Sort by weight (later lines have higher weight)
            all_letters.sort(key=lambda x: x[1], reverse=True)
            answer = all_letters[0][0]
            logging.info(f"Weighted fallback extracted answer: {answer}")
            return answer
            
        logging.error("Could not extract answer from LLM response")
        return "A"  # Default fallback
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"  # Default fallback