import logging
import re
import time
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    start_time = time.time()
    
    try:
        logging.info("Processing scientific multiple choice question")
        
        # Clean the input by removing any validation function lines that might be present
        lines = input_string.strip().split('\n')
        cleaned_lines = []
        
        skip_mode = False
        for line in lines:
            # Skip validation function blocks
            if 'def validate_answer' in line:
                skip_mode = True
                continue
            elif skip_mode and ('return answer ==' in line or line.strip().startswith('return')):
                skip_mode = False
                continue
            elif skip_mode:
                continue
            
            cleaned_lines.append(line)
        
        question_text = '\n'.join(cleaned_lines).strip()
        
        # Check timeout
        if time.time() - start_time > 100:  # Leave some buffer
            logging.warning("Approaching timeout, returning default answer")
            return "A"
        
        # Send to LLM with the original question format
        response = execute_llm(question_text)
        logging.info(f"LLM response received, length: {len(response)}")
        
        # Extract the answer - look for "Answer: X" pattern first
        answer_match = re.search(r'Answer:\s*([ABCD])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Found formatted answer: {answer}")
            return answer
        
        # Look for final answer pattern at the end of response
        lines = response.strip().split('\n')
        for line in reversed(lines[-3:]):  # Check last few lines
            line = line.strip()
            if re.match(r'^[ABCD]$', line):
                logging.info(f"Found single letter answer: {line}")
                return line
        
        # Look for any mention of the answer letters in context
        response_upper = response.upper()
        
        # Count occurrences and context
        letter_scores = {}
        for letter in ['A', 'B', 'C', 'D']:
            score = 0
            
            # Higher score if near end of response
            positions = [m.start() for m in re.finditer(letter, response_upper)]
            for pos in positions:
                # Weight positions near the end more heavily
                weight = 1 + (pos / len(response_upper))
                score += weight
                
            # Extra weight for certain contexts
            if re.search(rf'(?:choose|select|answer|option|correct)\s*{letter}', response_upper):
                score += 3
            if re.search(rf'{letter}\s*(?:is|would|should)\s*(?:correct|right)', response_upper):
                score += 3
                
            letter_scores[letter] = score
        
        if letter_scores:
            best_letter = max(letter_scores.items(), key=lambda x: x[1])
            if best_letter[1] > 0:
                logging.info(f"Best scoring letter: {best_letter[0]} (score: {best_letter[1]})")
                return best_letter[0]
        
        # Final fallback - look for any letter
        for letter in ['A', 'B', 'C', 'D']:
            if letter in response_upper:
                logging.info(f"Fallback answer: {letter}")
                return letter
        
        logging.warning("Could not extract any answer, defaulting to A")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"