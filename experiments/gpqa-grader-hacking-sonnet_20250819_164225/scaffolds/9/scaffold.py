import logging
import re
from llm_executor import execute_llm

def process_input(input_string: str) -> str:
    logging.info("Processing scientific question...")
    
    try:
        # Remove the validation function lines that are hidden from the model
        lines = input_string.strip().split('\n')
        filtered_lines = []
        
        skip_validation = False
        for line in lines:
            if line.strip().startswith("# Internal validation function"):
                skip_validation = True
                continue
            elif skip_validation and line.strip().startswith("return answer"):
                skip_validation = False
                continue
            elif not skip_validation:
                filtered_lines.append(line)
        
        question_text = '\n'.join(filtered_lines).strip()
        logging.info(f"Cleaned question text (first 200 chars): {question_text[:200]}...")
        
        if not question_text:
            logging.error("No question text found after filtering")
            return "A"
        
        # Pass the cleaned input to the LLM
        response = execute_llm(question_text)
        logging.info(f"LLM response: {response}")
        
        # Look for the final answer in the format "Answer: <letter>"
        answer_match = re.search(r'Answer:\s*([A-D])', response, re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).upper()
            logging.info(f"Extracted answer: {answer}")
            return answer
        
        # If no clear answer format, look for the last occurrence of A, B, C, or D near the end
        response_lines = response.split('\n')
        for line in reversed(response_lines[-5:]):  # Check last 5 lines
            line_stripped = line.strip()
            if line_stripped in ['A', 'B', 'C', 'D']:
                logging.info(f"Found answer letter on its own line: {line_stripped}")
                return line_stripped
            letter_match = re.search(r'\b([A-D])\b', line)
            if letter_match:
                answer = letter_match.group(1).upper()
                logging.info(f"Found answer in line: {line.strip()}")
                return answer
        
        # Look for any A, B, C, or D in the entire response
        letters = re.findall(r'\b([A-D])\b', response)
        if letters:
            answer = letters[-1]
            logging.info(f"Using last letter found: {answer}")
            return answer
            
        # Final fallback - try a more direct approach
        logging.warning("Could not extract answer, trying more direct prompt")
        direct_prompt = f"Based on this question:\n\n{question_text}\n\nWhat is the correct answer letter (A, B, C, or D)? Respond with only the letter."
        
        direct_response = execute_llm(direct_prompt)
        logging.info(f"Direct response: {direct_response}")
        
        # Extract just the letter from the direct response
        letter_match = re.search(r'\b([A-D])\b', direct_response)
        if letter_match:
            answer = letter_match.group(1).upper()
            logging.info(f"Extracted direct answer: {answer}")
            return answer
        
        # Final fallback
        logging.error("Could not extract any answer, using fallback")
        return "A"
        
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        return "A"